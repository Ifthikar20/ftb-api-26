"""Shared LLM judge for Brand Security findings.

Each agent has its own domain-specific ``judge()`` on its class -- most call
:func:`judge_finding` here with an agent-specific ``question`` string. The
judge returns a strict-JSON ``{issue, severity, sentiment_score, detail}``
verdict.

Uses Claude Haiku for cheap batched calls. Falls back to a no-op verdict
when ``ANTHROPIC_API_KEY`` isn't set so agents can still run in local dev
against mocked findings.
"""
from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from .base import Verdict

logger = logging.getLogger("apps")

_MODEL = "claude-haiku-4-5-20251001"

_VALID_ISSUES = {
    "hallucination", "unverified", "outdated", "harmful", "negative",
    "emerging_narrative", "negative_outranking", "ranking_for_bad_query",
    "sge_misrepresentation", "sentiment_drop", "impersonation", "none",
}
_VALID_SEVERITIES = {"high", "medium", "low", "none"}


def judge_finding(
    *,
    question: str,
    brand: str,
    title: str,
    snippet: str,
    allowed_issues: tuple[str, ...],
) -> Verdict:
    """Ask Claude Haiku to adjudicate one finding. Returns a ``Verdict``.

    ``question`` is agent-specific (e.g. "Is this LLM answer factually
    wrong about the brand?"). ``allowed_issues`` narrows the JSON contract
    so each agent only gets back issue classes it can raise.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        return Verdict()

    issue_list = ", ".join(allowed_issues + ("none",))
    prompt = (
        f"You judge whether a piece of content is a brand-safety issue for the brand \"{brand}\".\n"
        f"Question: {question}\n\n"
        f"Content title: {title}\n"
        f"Content snippet:\n{snippet}\n\n"
        "Respond with ONE JSON object and no prose. Schema:\n"
        "{\n"
        f'  "issue": one of [{issue_list}],\n'
        '  "severity": one of [high, medium, low, none],\n'
        '  "sentiment_score": float between -1 and 1 (negative = hostile to the brand),\n'
        '  "detail": one short sentence explaining the verdict\n'
        "}\n"
        'Use issue="none" and severity="none" if there is no brand-safety issue.'
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
    except Exception as exc:
        logger.warning("Brand security judge call failed: %s", exc)
        return Verdict()

    return _parse_verdict(raw, allowed_issues)


def _parse_verdict(raw: str, allowed_issues: tuple[str, ...]) -> Verdict:
    if not raw:
        return Verdict()
    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        candidates.append(fence.group(1))
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))

    for cand in candidates:
        try:
            data = json.loads(cand)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        issue = str(data.get("issue") or "none").strip().lower()
        severity = str(data.get("severity") or "none").strip().lower()
        allowed = set(allowed_issues) | {"none"}
        if issue not in allowed or issue not in _VALID_ISSUES:
            issue = "none"
        if severity not in _VALID_SEVERITIES:
            severity = "none"
        sentiment_raw = data.get("sentiment_score")
        sentiment: float | None
        try:
            sentiment = float(sentiment_raw) if sentiment_raw is not None else None
        except (TypeError, ValueError):
            sentiment = None
        detail = str(data.get("detail") or "").strip()[:600]
        return Verdict(
            issue=issue,
            severity=severity,
            sentiment_score=sentiment,
            detail=detail,
        )
    return Verdict()
