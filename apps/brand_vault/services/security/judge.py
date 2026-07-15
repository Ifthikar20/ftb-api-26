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

# Maximum characters of brand ground-truth to include in a single judge
# prompt. Enough for ~5 medium-sized chunks, well under the model's
# context window.
_MAX_GROUND_TRUTH_CHARS = 4000

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
    ground_truth: list[dict] | None = None,
) -> Verdict:
    """Ask Claude Haiku to adjudicate one finding. Returns a ``Verdict``.

    ``question`` is agent-specific (e.g. "Is this LLM answer factually
    wrong about the brand?"). ``allowed_issues`` narrows the JSON contract
    so each agent only gets back issue classes it can raise.

    ``ground_truth`` is an optional list of retrieval hits from the
    client's own RAG knowledge base (dicts with at least ``text`` and
    ``section_label``). When provided, the judge is told to prefer the
    client's stated facts over its own priors, which converts vague
    "does this sound off" adjudication into concrete contradiction
    checking against the client's uploaded brand material.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        return Verdict()

    issue_list = ", ".join(allowed_issues + ("none",))
    ground_truth_block = _format_ground_truth(ground_truth or [])
    if ground_truth_block:
        grounding_preamble = (
            "The client has provided the following statements about their own brand. "
            "Treat these as the source of truth. If the content contradicts, "
            "omits, or misrepresents them, flag it. If the content is consistent, "
            'return issue="none".\n\n'
            f"{ground_truth_block}\n\n"
        )
    else:
        grounding_preamble = (
            "The client has not uploaded any brand reference material yet, so "
            "judge using general reasoning only. Be conservative: prefer "
            'issue="none" unless the content is clearly wrong or harmful.\n\n'
        )

    prompt = (
        f"You judge whether a piece of content is a brand-safety issue for the brand \"{brand}\".\n"
        f"Question: {question}\n\n"
        f"{grounding_preamble}"
        f"Content title: {title}\n"
        f"Content snippet:\n{snippet}\n\n"
        "Respond with ONE JSON object and no prose. Schema:\n"
        "{\n"
        f'  "issue": one of [{issue_list}],\n'
        '  "severity": one of [high, medium, low, none],\n'
        '  "sentiment_score": float between -1 and 1 (negative = hostile to the brand),\n'
        '  "detail": one short sentence explaining the verdict, citing the brand'
        ' fact that was contradicted when applicable\n'
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


def _format_ground_truth(hits: list[dict]) -> str:
    """Render retrieval hits as a bounded ``=== BRAND GROUND TRUTH ===`` block."""
    if not hits:
        return ""
    lines = ["=== BRAND GROUND TRUTH ==="]
    used = len(lines[0]) + 1
    for i, h in enumerate(hits, start=1):
        label = (h.get("section_label") or h.get("source_url") or "brand source")[:120]
        text = (h.get("text") or "").strip()
        if not text:
            continue
        block = f"[{i}] {label}\n{text}"
        if used + len(block) > _MAX_GROUND_TRUTH_CHARS:
            break
        lines.append(block)
        used += len(block) + 1
    if len(lines) == 1:
        return ""
    return "\n\n".join(lines)


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
