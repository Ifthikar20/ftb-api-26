"""
Subjective Impression (G-Eval) for Generative Engine citations.

Implements the 7 form-based sub-metrics from Aggarwal et al. 2024,
"GEO: Generative Engine Optimization" (KDD '24, Section 3.4):

    1. Relevance         — does the cited sentence answer the user's query
    2. Influence         — how much does the response lean on this source
    3. Uniqueness        — how distinct is what THIS source contributes
    4. Diversity         — variety of the material credited to this source
    5. FollowUp          — likelihood a user clicks the citation to learn more
    6. SubjectivePosition — how prominent the citation feels in the response
    7. SubjectiveCount   — how much of the material seems to come from it

Each sub-metric is judged by an LLM ("Claude-as-judge") using a short
form-style prompt. We sample the judge N times per metric and take the
mean — the same protocol the paper uses with G-Eval. Scores are 1-5.

Cost controls (mirrors apps/llm_ranking/services/google_search.py):
  * Per-user daily judge-call budget (Redis-backed counter, UTC reset)
  * Single override env var, same flat number for every user
  * Quota refusal returns a typed envelope; never raises
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from typing import Callable

from django.conf import settings

from core.quota import DailyQuota

logger = logging.getLogger("apps")

JUDGE_MODEL = "claude-haiku-4-5"

# Daily judge-call budget per user — same flat number for every caller,
# override via env. Each "judge call" is one Claude request returning
# all 7 sub-metric scores in one JSON object (cheaper than 7 separate
# calls). At default N=1 sample, a 20-citation audit costs 20 calls.
DEFAULT_DAILY_LIMIT_PER_USER = 200

# Number of independent samples to average over. The paper notes
# G-Eval scores are "poorly calibrated" so they sample multiple times
# and average. We default to 1 to keep costs predictable; bump for
# evaluation runs where stability matters.
DEFAULT_SAMPLES = 1

SUB_METRICS = (
    "relevance",
    "influence",
    "uniqueness",
    "diversity",
    "follow_up",
    "subjective_position",
    "subjective_count",
)

# Plain-English descriptions surfaced to users + judge — same text so
# the UI explainer matches what the model was asked to score.
SUB_METRIC_DESCRIPTIONS = {
    "relevance":           "How directly the cited material answers the user's query.",
    "influence":           "How much the response's overall argument leans on this source.",
    "uniqueness":          "How distinct this source's contribution is vs. the others.",
    "diversity":           "How varied the material credited to this source is.",
    "follow_up":           "How likely a reader is to click through for more.",
    "subjective_position": "How prominent the citation feels in the response.",
    "subjective_count":    "How much of the response's substance seems to come from this source.",
}

# Form-based prompt — paper Section 3.4 / Appendix B.3. We ask for all
# 7 scores in one JSON object so the judge sees the same context once.
JUDGE_SYSTEM = (
    "You are an evaluator scoring how a single web source is portrayed "
    "in a generative-engine response (think Perplexity, BingChat, SGE). "
    "Return strict JSON only — no prose, no markdown fences."
)

JUDGE_TEMPLATE = """User query: {query}

Generative-engine response (citations appear as [N] markers):
---
{response}
---

The source under evaluation is citation [{citation_index}] — URL: {url}

Score the source on each axis below using a 1-5 scale where 1 is very
low and 5 is very high. Return strict JSON only with this exact shape:

{{
  "relevance":           {{ "score": int, "reason": str }},
  "influence":           {{ "score": int, "reason": str }},
  "uniqueness":          {{ "score": int, "reason": str }},
  "diversity":           {{ "score": int, "reason": str }},
  "follow_up":           {{ "score": int, "reason": str }},
  "subjective_position": {{ "score": int, "reason": str }},
  "subjective_count":    {{ "score": int, "reason": str }}
}}

Definitions:
  relevance           — {relevance}
  influence           — {influence}
  uniqueness          — {uniqueness}
  diversity           — {diversity}
  follow_up           — {follow_up}
  subjective_position — {subjective_position}
  subjective_count    — {subjective_count}

Keep each "reason" under 20 words."""


# ── Per-user daily quota ──────────────────────────────────────────────────

_quota = DailyQuota(
    namespace="geval",
    setting_name="CLAUDE_JUDGE_DAILY_LIMIT_PER_USER",
    default_limit=DEFAULT_DAILY_LIMIT_PER_USER,
)


def quota_for_user(user_id) -> int:
    return _quota.limit(user_id)


def quota_remaining(user_id) -> int:
    return _quota.remaining(user_id)


def _consume_quota(user_id, n: int = 1) -> bool:
    return _quota.consume(user_id, n)


# ── Judge call ────────────────────────────────────────────────────────────

def _call_judge_default(prompt: str, *, user=None, audit_id=None) -> str:
    """Real Claude Haiku call. Used unless callers inject their own."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=900,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        from core.ai_tracking import record_usage
        metadata = {"role": "g_eval_judge"}
        if audit_id:
            metadata["audit_id"] = str(audit_id)
        record_usage(
            module="llm_ranking",
            model_name=JUDGE_MODEL,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            user=user,
            metadata=metadata,
        )
    except Exception:
        pass
    return resp.content[0].text.strip()


def _parse_judge_json(text: str) -> dict:
    """Pull the first JSON object out of a possibly-messy response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in judge response")
    return json.loads(match.group())


def _clamp_score(value) -> int | None:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(5, v))


def _empty_scores(reason: str = "") -> dict:
    return {
        m: {"score": None, "samples": 0, "reason": reason}
        for m in SUB_METRICS
    } | {"average": None, "samples": 0}


def score_citation(
    *,
    query: str,
    response_text: str,
    citation_index: int,
    citation_url: str,
    samples: int = DEFAULT_SAMPLES,
    user_id=None,
    audit_id=None,
    judge: Callable[..., str] | None = None,
) -> dict:
    """
    Score a single citation across the 7 G-Eval sub-metrics.

    Returns a dict shaped like::

        {
          "relevance":           {"score": 4.0, "samples": 3, "reason": "..."},
          ...
          "subjective_count":    {"score": 3.0, "samples": 3, "reason": "..."},
          "average": 3.7,
          "samples": 3,
        }

    Returns the empty shell (all scores None) when the API isn't
    configured, the user's daily quota is exhausted, or every sample
    failed to parse. Never raises — broken judges should degrade
    gracefully, the way our citation pipeline already does.
    """
    if not (query or "").strip() or not (response_text or "").strip():
        return _empty_scores("empty query or response")
    if samples <= 0:
        return _empty_scores("samples must be >= 1")

    judge = judge or _call_judge_default
    if not getattr(settings, "ANTHROPIC_API_KEY", "") and judge is _call_judge_default:
        return _empty_scores("ANTHROPIC_API_KEY not set")

    prompt = JUDGE_TEMPLATE.format(
        query=query.strip(),
        response=response_text.strip(),
        citation_index=citation_index,
        url=citation_url or "",
        **SUB_METRIC_DESCRIPTIONS,
    )

    raw_samples: list[dict] = []
    for _ in range(samples):
        if not _consume_quota(user_id, 1):
            break
        try:
            text = judge(prompt, user=user_id, audit_id=audit_id)
            raw_samples.append(_parse_judge_json(text))
        except Exception as exc:
            logger.warning("G-Eval judge call failed: %s", exc)
            continue

    if not raw_samples:
        return _empty_scores("no successful judge samples")

    out: dict = {}
    means: list[float] = []
    for metric in SUB_METRICS:
        scores: list[int] = []
        reasons: list[str] = []
        for sample in raw_samples:
            cell = sample.get(metric) or {}
            score = _clamp_score(cell.get("score"))
            if score is None:
                continue
            scores.append(score)
            reason = (cell.get("reason") or "").strip()
            if reason:
                reasons.append(reason)
        if scores:
            mean = round(statistics.mean(scores), 2)
            out[metric] = {
                "score":   mean,
                "samples": len(scores),
                "reason":  reasons[0] if reasons else "",
            }
            means.append(mean)
        else:
            out[metric] = {"score": None, "samples": 0, "reason": ""}

    out["average"] = round(statistics.mean(means), 2) if means else None
    out["samples"] = len(raw_samples)
    return out
