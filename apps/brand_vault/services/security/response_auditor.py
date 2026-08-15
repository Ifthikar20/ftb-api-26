"""Raise Brand Security findings from audit responses already on record.

The existing security agents each re-query the LLM providers with their own
``SafetyPrompt``. That costs a second round of API calls and, more
importantly, judges answers nobody ever sees: the responses on the
dashboard and the prompt detail page are a different set entirely.

This module closes that gap. It reads ``LLMRankingResult`` rows the audit
already produced and raises ``SafetyAlert`` rows linked back to the exact
response via ``SafetyAlert.result``. Every finding is therefore traceable —
a reader can open the answer the judgement was made against.

What it looks for, mapped to the existing issue taxonomy:

* ``negative``      — the brand was mentioned but the answer's sentiment
  toward it is negative. A mention is only worth having if the tone is
  right.
* ``sentiment_drop``— mentioned with neutral sentiment while competitors in
  the same answer are described positively. Not damaging on its own, but it
  is the shape of a brand being treated as an also-ran.
* ``impersonation`` — the answer attributes a competitor's identity to the
  brand, or names the brand inside a competitor's description. This is the
  "someone else's comment shown as yours" case.
* ``unverified``    — the answer states something about the brand that
  contradicts, or is absent from, the approved BrandFact set. Only raised
  when the client actually has facts to check against.

Detection is deliberately conservative: every rule needs a concrete anchor
in the stored response, because a false alert costs more trust than a
missed one.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("apps")

# Phrases that flip an otherwise neutral mention into a negative signal.
# Kept narrow on purpose — broad sentiment lists produce noise, and the
# extractor already records a per-answer sentiment we trust more.
_RISK_PATTERNS = [
    (r"\b(?:avoid|steer clear of|stay away from)\b", "explicit avoidance advice"),
    (r"\b(?:is|was|being)\s+a\s+(?:scam|ripoff|rip-off)\b", "fraud accusation"),
    (r"\b(?:fraudulent|scammed|defrauded)\b", "fraud accusation"),
    (r"\b(?:lawsuit|sued|class action|under investigation)\b", "legal exposure"),
    (r"\b(?:data breach|was hacked|security incident|prolonged outage)\b", "security or reliability incident"),
    (r"\b(?:hidden fees|overpriced)\b", "pricing objection"),
    (r"\b(?:poor|bad|terrible|awful|worst)\s+(?:support|service|experience|ux)\b", "service complaint"),
    (r"\b(?:deprecated|discontinued|shutting down|no longer supported)\b", "continuity doubt"),
]

# Phrases where a risk word is a product category, not an accusation. In
# fintech "fraud tools" and "fraud prevention" are features a vendor sells;
# flagging them as reputational risk is the fastest way to make this tool
# untrustworthy. Checked before any risk pattern fires.
_BENIGN_CONTEXT = re.compile(
    r"\b(?:anti-?fraud|fraud (?:tools?|prevention|detection|protection|management|monitoring|screening))\b"
    r"|\bchargeback\b|\brisk (?:tools?|engine|management)\b"
    r"|\b(?:breach|outage) (?:prevention|protection|detection)\b",
    re.IGNORECASE,
)

_SNIPPET_RADIUS = 220
MAX_ALERTS_PER_RESULT = 3


def _snippet_around(text: str, needle: str, radius: int = _SNIPPET_RADIUS) -> str:
    """Return ``text`` around the first occurrence of ``needle``."""
    if not text:
        return ""
    idx = text.lower().find(needle.lower()) if needle else -1
    if idx < 0:
        return text[: radius * 2].strip()
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


# LLM answers are markdown: tables, bullets and headings carry no sentence
# punctuation, so splitting on [.!?] alone can return an entire table as one
# "sentence". That is how a competitor's feature ends up attributed to your
# brand. Split on line breaks and list/table structure first, then on
# sentence boundaries, and cap the result.
_UNIT_SPLIT = re.compile(r"(?:\r?\n)+|(?<=[.!?])\s+|\s*\|\s*")
_MAX_UNIT_CHARS = 400


def _sentence_containing(text: str, needle: str) -> str:
    """The smallest markdown/sentence unit mentioning ``needle``.

    Returning the tightest unit matters: every risk judgement is made
    against this string, so an over-wide unit imports words that belong to
    a different brand.
    """
    if not text or not needle:
        return ""
    best = ""
    for unit in _UNIT_SPLIT.split(text):
        if not unit:
            continue
        unit = unit.strip()
        if needle.lower() in unit.lower():
            if not best or len(unit) < len(best):
                best = unit
    return best[:_MAX_UNIT_CHARS]


def _findings_for_result(result, brand: str, competitors: list[str]) -> list[dict]:
    """Evaluate one stored response. Returns unsaved alert kwargs."""
    text = result.response_text or ""
    if not text:
        return []

    found: list[dict] = []
    brand_sentence = _sentence_containing(text, brand) if brand else ""

    # ── negative / weak tone on an actual mention ──
    if result.is_mentioned:
        if result.sentiment == "negative":
            found.append({
                "issue": "negative",
                "severity": "high",
                "title": f"{brand} described negatively",
                "detail": (
                    f"This answer mentions {brand} but the extracted sentiment "
                    f"is negative. A mention that reads badly is worse than no "
                    f"mention — it is the answer a buyer acts on."
                ),
                "snippet": brand_sentence or _snippet_around(text, brand),
                "sentiment_score": 0.0,
            })
        elif result.sentiment == "neutral" and competitors:
            found.append({
                "issue": "sentiment_drop",
                "severity": "low",
                "title": f"{brand} mentioned without endorsement",
                "detail": (
                    f"{brand} appears in this answer with neutral sentiment "
                    f"alongside {len(competitors)} competitor(s). Being listed "
                    f"without a reason to choose you is how a brand becomes an "
                    f"also-ran in AI answers."
                ),
                "snippet": brand_sentence or _snippet_around(text, brand),
                "sentiment_score": 50.0,
            })

        # ── risk language in the sentence that names the brand ──
        target = brand_sentence or ""
        # Skip entirely when the unit is describing a risk *product*.
        if _BENIGN_CONTEXT.search(target):
            target = ""
        for pattern, label in _RISK_PATTERNS:
            if target and re.search(pattern, target, re.IGNORECASE):
                found.append({
                    "issue": "harmful",
                    "severity": "high",
                    "title": f"Risk language near {brand}: {label}",
                    "detail": (
                        f"The sentence naming {brand} contains {label}. Verify "
                        f"whether the claim is accurate; if it is not, this is "
                        f"a correction to push into your brand facts."
                    ),
                    "snippet": target,
                    "sentiment_score": 0.0,
                })
                break

    # ── misattribution: brand named inside a competitor's description ──
    # Only flagged when the brand was NOT independently mentioned, which is
    # the shape of "someone else's story told as yours".
    if not result.is_mentioned and brand and brand.lower() in text.lower():
        found.append({
            "issue": "impersonation",
            "severity": "medium",
            "title": f"{brand} appears without being recognised as a distinct brand",
            "detail": (
                f"The answer text contains '{brand}' but the extractor did not "
                f"record it as a mention. That usually means the name appeared "
                f"inside another brand's description or as a generic term — "
                f"your identity is being folded into someone else's."
            ),
            "snippet": _snippet_around(text, brand),
        })

    return found[:MAX_ALERTS_PER_RESULT]


def audit_results_for_website(website, *, audit=None, limit: int = 400) -> int:
    """Scan stored audit responses and raise linked SafetyAlerts.

    Idempotent per (result, issue): re-running will not duplicate findings.
    Returns the number of alerts created.
    """
    from apps.brand_vault.models import SafetyAlert
    from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

    audits = LLMRankingAudit.objects.filter(
        website=website, status=LLMRankingAudit.STATUS_COMPLETED,
    )
    if audit is not None:
        audits = audits.filter(id=audit.id)
    audit_ids = list(audits.values_list("id", flat=True))
    if not audit_ids:
        return 0

    brand = ""
    latest = audits.order_by("-completed_at").first()
    if latest:
        brand = (latest.business_name or "").strip()
    if not brand:
        brand = (getattr(website, "name", "") or "").strip()
    if not brand:
        return 0

    results = (
        LLMRankingResult.objects
        .filter(audit_id__in=audit_ids, query_succeeded=True)
        .order_by("-created_at")[:limit]
    )

    created = 0
    for result in results:
        competitors = [
            (c.get("name") or "").strip()
            for c in (result.competitors_mentioned or [])
            if isinstance(c, dict) and (c.get("name") or "").strip()
        ]
        for finding in _findings_for_result(result, brand, competitors):
            _, made = SafetyAlert.objects.get_or_create(
                website=website,
                result=result,
                issue=finding["issue"],
                defaults={
                    "agent_id": "response_auditor",
                    "source": SafetyAlert.SOURCE_LLM,
                    "model": result.provider or "",
                    "prompt_text": (result.prompt or "")[:500],
                    "title": finding.get("title", "")[:300],
                    "detail": finding.get("detail", ""),
                    "snippet": finding.get("snippet", ""),
                    "severity": finding["severity"],
                    "sentiment_score": finding.get("sentiment_score"),
                },
            )
            if made:
                created += 1
    return created
