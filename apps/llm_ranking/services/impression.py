"""
Impression metrics for Generative Engine responses.

Implements two metrics from Aggarwal et al. 2024, "GEO: Generative
Engine Optimization" (KDD '24, arXiv:2311.09735v3):

  * Position-Adjusted Word Count (Imp_pwc) — eq. 3
        Imp_pwc(c_i, r) = sum over s in S_{c_i}  |s| * exp(-pos(s)/|S_r|)
                          ---------------------------------------------
                                  sum over s in S_r  |s|

    where S_r is the set of sentences in response r, S_{c_i} is the
    subset that cite source c_i, |s| is the word count of sentence s,
    and pos(s) is the 0-indexed position of s in S_r. Sentences near
    the top decay slowest — they're the ones the user actually reads.

  * Relative Improvement (eq. 4)
        (Imp(r') - Imp(r)) / Imp(r) * 100

    Used to project the lift a content rewrite would produce, given
    that we have a baseline impression and a hypothetical post-rewrite
    impression. We also expose a static lookup of the paper's measured
    average lifts per GEO rewrite method (Table 1) so we can answer
    "what is THIS strategy projected to deliver?" without actually
    running the rewrite ourselves.

The functions here are pure — no Django, no I/O — so they can be
unit-tested in isolation and reused from tasks, the GEO recommender,
and any future evaluation harness.
"""
from __future__ import annotations

import math
import re
from typing import Iterable

# ── Sentence + citation parsing ───────────────────────────────────────────

# Split on sentence-ending punctuation followed by whitespace. Not
# perfect (won't handle "Dr. Smith") but matches the paper's coarse
# definition of a sentence well enough for a citation-weighted metric.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Inline citation markers we recognize in the response:
#   [1]        single
#   [1][2]     adjacent
#   [1, 2]     comma-list
#   [1,2,3]    comma-list (no spaces)
# We deliberately do NOT match [foo] / [http...] — only digit groups.
_CITATION_BLOCK = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def _split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def _word_count(sentence: str) -> int:
    # Strip citation markers before counting so "[1] [2]" doesn't pad
    # the length of an otherwise-empty sentence.
    cleaned = _CITATION_BLOCK.sub("", sentence)
    return len([w for w in cleaned.split() if w])


def _citations_in_sentence(sentence: str) -> set[int]:
    found: set[int] = set()
    for match in _CITATION_BLOCK.finditer(sentence):
        for num in match.group(1).split(","):
            num = num.strip()
            if num.isdigit():
                found.add(int(num))
    return found


# ── Imp_pwc (paper eq. 3) ────────────────────────────────────────────────

def position_adjusted_word_counts(
    response_text: str,
    *,
    source_indices: Iterable[int] | None = None,
) -> dict[int, float]:
    """
    Compute Imp_pwc for every cited source in ``response_text``.

    Returns ``{source_index: score}`` where ``source_index`` is the
    1-indexed citation marker as it appears in the text (so ``[3]``
    becomes key ``3``). If ``source_indices`` is given, the result is
    padded so every requested index appears, with 0.0 for uncited
    sources — handy when the caller wants a stable shape per source.

    Returns ``{}`` when the response is empty.
    """
    sentences = _split_sentences(response_text)
    if not sentences:
        return {idx: 0.0 for idx in (source_indices or [])}

    total_words = sum(_word_count(s) for s in sentences)
    if total_words <= 0:
        return {idx: 0.0 for idx in (source_indices or [])}

    n = len(sentences)
    scores: dict[int, float] = {}
    for pos, sentence in enumerate(sentences):
        cites = _citations_in_sentence(sentence)
        if not cites:
            continue
        w = _word_count(sentence)
        if w <= 0:
            continue
        # Paper eq. 3: exponential decay on the 0-indexed sentence
        # position, normalized by the response length so longer
        # responses don't artificially flatten the curve.
        decay = math.exp(-pos / n)
        contribution = w * decay
        for src in cites:
            scores[src] = scores.get(src, 0.0) + contribution

    # Normalize by total word count, exactly as in the paper.
    for src, raw in list(scores.items()):
        scores[src] = raw / total_words

    if source_indices is not None:
        for idx in source_indices:
            scores.setdefault(idx, 0.0)
    return scores


def word_count_impression(
    response_text: str,
    *,
    source_indices: Iterable[int] | None = None,
) -> dict[int, float]:
    """
    The simpler "Word Count" impression metric from paper eq. 2 — no
    positional decay. Kept around because the paper also reports it as
    a sub-metric, and because it's a useful baseline when comparing
    against Imp_pwc to gauge how much position is moving the needle.
    """
    sentences = _split_sentences(response_text)
    if not sentences:
        return {idx: 0.0 for idx in (source_indices or [])}
    total_words = sum(_word_count(s) for s in sentences)
    if total_words <= 0:
        return {idx: 0.0 for idx in (source_indices or [])}

    scores: dict[int, float] = {}
    for sentence in sentences:
        cites = _citations_in_sentence(sentence)
        if not cites:
            continue
        w = _word_count(sentence)
        for src in cites:
            scores[src] = scores.get(src, 0.0) + w

    for src, raw in list(scores.items()):
        scores[src] = raw / total_words

    if source_indices is not None:
        for idx in source_indices:
            scores.setdefault(idx, 0.0)
    return scores


# ── Relative improvement (paper eq. 4) ────────────────────────────────────

def relative_improvement(before: float, after: float) -> float | None:
    """
    Percent lift in impression from baseline ``before`` to post-rewrite
    ``after``. Returns ``None`` when ``before`` is non-positive — a
    relative metric is undefined against a zero baseline (the source
    wasn't cited at all, so any post-rewrite citation is an infinite
    multiplier; the UI should fall back to the absolute Imp_pwc).
    """
    if before is None or after is None:
        return None
    if before <= 0:
        return None
    return (after - before) / before * 100.0


# ── Projected lift per GEO rewrite method (paper Table 1) ────────────────
#
# Average Position-Adjusted Word Count lift over the GEO-bench dataset.
# Computed as (method_pwc / baseline_pwc - 1) * 100 from Table 1,
# baseline = 19.3 (the "No Optimization" row). These are domain-agnostic
# averages — for domain-specific picks see ``_DOMAIN_BEST_METHOD``.
PROJECTED_LIFT_PCT: dict[str, float] = {
    # Top performers (paper Section 4)
    "quotation_addition":  41.0,   # 27.2 vs 19.3 baseline
    "statistics_addition": 32.1,   # 25.5 vs 19.3
    "fluency_optimization": 28.0,  # 24.7 vs 19.3
    "cite_sources":        27.5,   # 24.6 vs 19.3
    "authoritative":       10.4,   # 21.3 vs 19.3
    "easy_to_understand":  14.0,   # 22.0 vs 19.3
    "technical_terms":     17.6,   # 22.7 vs 19.3
    # Non-performers — flagged so the UI can refuse to recommend them.
    "keyword_stuffing":    -8.3,   # 17.7 — actively HURTS
    "unique_words":        6.2,    # 20.5 — within noise
}

# Domain → recommended method (paper Table 3, "Top Performing Tags",
# Rank 1 only). Used by the recommender to pick the right rewrite for
# the user's query domain instead of always reaching for "Cite Sources".
_DOMAIN_BEST_METHOD: dict[str, str] = {
    "debate":          "authoritative",
    "business":        "fluency_optimization",
    "science":         "fluency_optimization",
    "statement":       "cite_sources",
    "facts":           "cite_sources",
    "law":             "cite_sources",
    "law & government": "statistics_addition",
    "people & society": "quotation_addition",
    "explanation":     "quotation_addition",
    "history":         "quotation_addition",
    "opinion":         "statistics_addition",
    "health":          "fluency_optimization",
}


def projected_lift(method: str) -> float | None:
    """Average lift in Imp_pwc from applying ``method`` (paper Table 1)."""
    return PROJECTED_LIFT_PCT.get((method or "").lower())


def best_method_for_domain(domain: str | None) -> str:
    """
    Recommend a GEO rewrite method for ``domain``. Falls back to
    ``quotation_addition`` (paper's best overall, +41%) when the
    domain is unknown or missing.
    """
    if domain:
        m = _DOMAIN_BEST_METHOD.get(domain.strip().lower())
        if m:
            return m
    return "quotation_addition"
