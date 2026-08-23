"""
GEO content-rewrite actions for the Source Influence page.

Implements 5 of the 9 strategies from Aggarwal et al. 2024, "GEO:
Generative Engine Optimization" (KDD '24, Section 2.2.2). We deliberately
exclude two:

  * keyword_stuffing — paper shows it REGRESSES visibility (17.7 vs 19.3
    Position-Adjusted Word Count baseline).
  * unique_words     — within-noise change (20.5 vs 19.3); not worth
    the rewrite cost.

The five we ship match the paper's top-performers in Table 1 plus
"authoritative" (a tone-only change that's useful for debate-style
domains, paper Table 3):

    method              avg Imp_pwc lift (Table 1)
    ─────────────────────────────────────────────
    quotation_addition  +41.0%
    statistics_addition +32.1%
    fluency_optimization +28.0%
    cite_sources        +27.5%
    authoritative       +10.4%

Each method is a black-box prompt-driven rewrite of the user's source
text — no domain knowledge baked in. The function returns the
rewritten text plus diff stats so the UI can show a side-by-side
before/after and the user can decide whether to publish the change.

Cost controls mirror google_search.py + subjective_impression.py:
flat per-user daily call budget, single env var, never raises.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from django.conf import settings

from core.llm import ClaudeUtility
from core.quota import DailyQuota

logger = logging.getLogger("apps")

REWRITE_MODEL = "claude-sonnet-4-5-20250929"

# Daily rewrite budget per user. Rewrites are larger (full document
# in, full document out) so this cap is smaller than the judge cap.
DEFAULT_DAILY_LIMIT_PER_USER = 30

# Hard cap on per-rewrite output to stop a runaway response from
# blowing the budget on a single call.
MAX_OUTPUT_TOKENS = 4096

# Method registry. Each entry holds (a) the system instruction we send
# to the LLM, (b) a human-friendly label, (c) a one-sentence "why" we
# show in the UI, and (d) the average projected lift from paper Table 1.
METHODS: dict[str, dict] = {
    "quotation_addition": {
        "label":  "Add a quotation",
        "why":    "Insert one relevant quotation from a credible source.",
        "lift":   41.0,
        "system": (
            "You rewrite a snippet of web content to add ONE relevant "
            "quotation from a credible, well-known source (a recognized "
            "expert, institution, or publication). The quotation must "
            "support the existing argument — do not introduce a new "
            "thesis. Attribute the speaker inline. Keep the rest of the "
            "text intact. Return only the rewritten text, no commentary."
        ),
    },
    "statistics_addition": {
        "label":  "Add a statistic",
        "why":    "Replace a qualitative claim with a concrete statistic.",
        "lift":   32.1,
        "system": (
            "You rewrite a snippet of web content to add ONE relevant, "
            "verifiable statistic that supports the existing argument. "
            "Prefer numbers from authoritative sources (government data, "
            "peer-reviewed research, industry reports). Cite the source "
            "in parentheses. Do not invent figures. Return only the "
            "rewritten text, no commentary."
        ),
    },
    "fluency_optimization": {
        "label":  "Optimize fluency",
        "why":    "Tighten prose without changing meaning or claims.",
        "lift":   28.0,
        "system": (
            "You rewrite a snippet of web content for fluency. Improve "
            "readability, vary sentence length, and remove filler words "
            "and clichés. Do not change the factual claims, the order of "
            "ideas, or the overall length by more than 10%. Return only "
            "the rewritten text, no commentary."
        ),
    },
    "cite_sources": {
        "label":  "Cite a source",
        "why":    "Anchor the strongest claim with a primary-source citation.",
        "lift":   27.5,
        "system": (
            "You rewrite a snippet of web content to add ONE inline "
            "citation backing the most important factual claim. Prefer "
            "primary sources (the original study, the official report, "
            "the canonical reference). Use a parenthetical citation in "
            "the form '(Source, Year)' or a footnote-style marker. Do "
            "not invent sources. Return only the rewritten text."
        ),
    },
    "authoritative": {
        "label":  "More authoritative tone",
        "why":    "Rewrite in a more confident, expert voice.",
        "lift":   10.4,
        "system": (
            "You rewrite a snippet of web content to sound more "
            "authoritative and expert. Use precise vocabulary, active "
            "voice, and decisive framing. Do not exaggerate, fabricate "
            "credentials, or change the factual claims. Return only the "
            "rewritten text, no commentary."
        ),
    },
}

ALLOWED_METHODS = frozenset(METHODS.keys())


# ── Per-user daily quota ──────────────────────────────────────────────────

_quota = DailyQuota(
    namespace="georewrite",
    setting_name="CLAUDE_REWRITE_DAILY_LIMIT_PER_USER",
    default_limit=DEFAULT_DAILY_LIMIT_PER_USER,
)


def quota_for_user(user_id) -> int:
    return _quota.limit(user_id)


def quota_remaining(user_id) -> int:
    return _quota.remaining(user_id)


def _consume_quota(user_id, n: int = 1) -> bool:
    return _quota.consume(user_id, n)


# ── Rewrite ───────────────────────────────────────────────────────────────

def _call_rewriter_default(
    *, system: str, user_prompt: str, user=None, audit_id=None,
) -> str:
    """Real Claude Sonnet call. Used unless callers inject their own.

    Goes through the central LLM gateway (spend-wall, rate-limit/breaker,
    usage recording with role=geo_rewrite). Raises on failure so
    ``rewrite`` can map it to its ``rewriter_error`` envelope.
    """
    result = ClaudeUtility(model=REWRITE_MODEL, max_tokens=MAX_OUTPUT_TOKENS).query(
        user_prompt,
        system_prompt=system,
        user=user,
        audit_id=audit_id,
        role="geo_rewrite",
        module="llm_ranking",
    )
    if not result.succeeded:
        raise RuntimeError(f"GEO rewrite call failed: {result.error}")
    return result.text


def _diff_stats(before: str, after: str) -> dict:
    """Cheap word-level diff summary for the UI."""
    bw = len(before.split())
    aw = len(after.split())
    delta = aw - bw
    return {
        "before_words": bw,
        "after_words":  aw,
        "delta_words":  delta,
        "pct_change":   round((delta / bw * 100), 1) if bw else None,
    }


def rewrite(
    *,
    source_text: str,
    method: str,
    query: str | None = None,
    user_id=None,
    audit_id=None,
    rewriter: Callable[..., str] | None = None,
) -> dict:
    """
    Rewrite ``source_text`` using a paper-validated GEO strategy.

    Returns::

        {
          "ok": bool,
          "method": "quotation_addition",
          "label": "Add a quotation",
          "why":   "...",
          "projected_lift_pct": 41.0,
          "rewritten":  "...rewritten copy...",
          "diff": {"before_words": 120, "after_words": 138, ...},
          "error": None | "quota_exceeded" | "unknown_method" | "judge_error",
        }

    Returns a shell with ``ok=False`` and a populated ``error`` rather
    than raising — the UI degrades gracefully.
    """
    method = (method or "").lower()
    if method not in ALLOWED_METHODS:
        return {
            "ok":     False,
            "method": method,
            "error":  "unknown_method",
            "allowed": sorted(ALLOWED_METHODS),
        }

    if not (source_text or "").strip():
        return {"ok": False, "method": method, "error": "empty_source"}

    rewriter = rewriter or _call_rewriter_default
    if (
        not getattr(settings, "ANTHROPIC_API_KEY", "")
        and rewriter is _call_rewriter_default
    ):
        return {"ok": False, "method": method, "error": "anthropic_key_missing"}

    if not _consume_quota(user_id, 1):
        return {
            "ok":     False,
            "method": method,
            "error":  "quota_exceeded",
            "daily_limit":    quota_for_user(user_id),
            "quota_remaining": 0,
        }

    spec = METHODS[method]
    user_prompt = (
        (f"Target query: {query.strip()}\n\n" if query and query.strip() else "")
        + "Source text:\n---\n"
        + source_text.strip()
        + "\n---"
    )

    try:
        rewritten = rewriter(
            system=spec["system"],
            user_prompt=user_prompt,
            user=user_id,
            audit_id=audit_id,
        )
    except Exception as exc:
        logger.warning("GEO rewrite (%s) failed: %s", method, exc)
        return {"ok": False, "method": method, "error": "rewriter_error"}

    return {
        "ok":     True,
        "method": method,
        "label":  spec["label"],
        "why":    spec["why"],
        "projected_lift_pct": spec["lift"],
        "rewritten": rewritten,
        "diff":      _diff_stats(source_text, rewritten),
        "quota_remaining": quota_remaining(user_id),
        "daily_limit":     quota_for_user(user_id),
    }
