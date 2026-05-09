"""Accuracy guard — verify draft claims against the brand vault.

Splits the draft into sentence-style claims, embeds each, and looks for
a sufficiently-similar approved BrandFact. ``score`` is the fraction of
claims that map to a vault fact above a similarity threshold; the notes
list claims that found no support.
"""
from __future__ import annotations

import logging
import re

from apps.brand_vault.models import BrandFact, FactStatus
from apps.brand_vault.services.embeddings import cosine_similarity, embed_text

logger = logging.getLogger("apps")

SIMILARITY_THRESHOLD = 0.55
MAX_CLAIMS = 25


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _extract_claims(text: str) -> list[str]:
    text = re.sub(r"^#.*$", "", text or "", flags=re.MULTILINE)
    text = re.sub(r"\*+", "", text)
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    # Filter to sentences that look like factual statements.
    out = []
    for s in sentences:
        if len(s) < 20 or len(s) > 400:
            continue
        if s.endswith("?"):
            continue
        out.append(s)
        if len(out) >= MAX_CLAIMS:
            break
    return out


def score_accuracy(draft) -> tuple[float, str]:
    """Return ``(score, notes)`` for a :class:`ContentDraft`."""
    claims = _extract_claims(draft.body_markdown or "")
    if not claims:
        return 1.0, "no factual claims detected"

    facts = list(
        BrandFact.objects.filter(
            website=draft.website,
            status__in=(FactStatus.APPROVED.value, FactStatus.AUTO.value),
            version_to__isnull=True,
        )[:200]
    )
    if not facts:
        return 0.5, "no approved facts in vault to verify against"

    fact_embs: list[list[float]] = []
    for f in facts:
        emb = f.embedding if isinstance(f.embedding, list) and f.embedding else None
        if not emb:
            try:
                emb = embed_text(f"{f.subject} {f.predicate} {f.object}")
            except Exception:
                emb = []
        fact_embs.append(emb or [])

    verified = 0
    unsupported: list[str] = []
    for claim in claims:
        try:
            ce = embed_text(claim)
        except Exception:
            ce = []
        if not ce:
            unsupported.append(claim[:120])
            continue
        best = 0.0
        for fe in fact_embs:
            if not fe:
                continue
            sim = cosine_similarity(ce, fe)
            if sim > best:
                best = sim
        if best >= SIMILARITY_THRESHOLD:
            verified += 1
        else:
            unsupported.append(claim[:120])

    total = len(claims)
    score = verified / total if total else 1.0
    if not unsupported:
        notes = f"all {total} detected claims map to approved facts"
    else:
        notes = (
            f"{verified}/{total} claims verified. Unsupported: "
            + " | ".join(unsupported[:5])
        )
    return score, notes
