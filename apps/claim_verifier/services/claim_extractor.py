"""Atomic-claim extraction from LLM ranking responses.

For one ``LLMRankingResult`` the extractor pulls the response text from
``raw_payload`` (falling back to ``response_text``), asks Claude for a
JSON array of (subject, predicate, object) tuples, filters to claims
whose subject mentions the brand or known competitors, embeds each
claim, and persists the rows.

Gated on ``CLAIM_VERIFICATION_ENABLED`` so the regular test suite can
opt out without burning Anthropic tokens.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List

from django.conf import settings

from apps.brand_vault.services.embeddings import embed_text
from apps.claim_verifier.models import Claim

logger = logging.getLogger("apps")

EXTRACTION_PROMPT = (
    "Read the following AI assistant response and extract atomic factual "
    "claims about the brand named '{brand}' and its competitors. Return "
    "ONLY a JSON array. Each element has fields: text (one short sentence), "
    "subject (string), predicate (string), object (string), confidence "
    "(float 0..1). No markdown, no commentary. Use [] if no claims.\n\n"
    "Response:\n{text}\n"
)


def _response_text(result) -> str:
    payload = getattr(result, "raw_payload", None) or {}
    if isinstance(payload, dict):
        for key in ("response_text", "text", "completion", "content"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                return v
    return getattr(result, "response_text", "") or ""


def _competitor_names(audit) -> list[str]:
    out: list[str] = []
    for r in (audit.results.all() if hasattr(audit, "results") else []):
        for c in (getattr(r, "competitors_mentioned", None) or []):
            if isinstance(c, dict):
                name = c.get("name", "") or c.get("brand", "")
            else:
                name = str(c)
            if name and name not in out:
                out.append(name)
    return out


def _parse_json_array(raw: str) -> list[dict]:
    if not raw:
        return []
    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        candidates.append(fence.group(1))
    bracket = re.search(r"\[.*\]", raw, re.DOTALL)
    if bracket:
        candidates.append(bracket.group(0))
    for cand in candidates:
        try:
            data = json.loads(cand)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except Exception:
            continue
    return []


def _call_llm(brand: str, text: str) -> list[dict]:
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        return []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(brand=brand, text=text),
            }],
        )
        return _parse_json_array(resp.content[0].text.strip())
    except Exception as exc:
        logger.warning("Claim extraction LLM call failed: %s", exc)
        return []


def _is_brand_subject(subject: str, brand: str, competitors: list[str]) -> bool:
    s = (subject or "").lower()
    if not s:
        return False
    if brand and brand.lower() in s:
        return True
    for c in competitors:
        if c and c.lower() in s:
            return True
    return False


def extract_claims_for_result(result_id: str) -> List[Claim]:
    """Run claim extraction for one LLMRankingResult."""
    if not getattr(settings, "CLAIM_VERIFICATION_ENABLED", True):
        return []
    from apps.llm_ranking.models import LLMRankingResult

    try:
        result = LLMRankingResult.objects.select_related(
            "audit", "audit__website",
        ).get(id=result_id)
    except LLMRankingResult.DoesNotExist:
        return []

    audit = result.audit
    website = audit.website
    brand = audit.business_name or (website.name if website else "")
    text = _response_text(result)
    if not text.strip():
        return []

    items = _call_llm(brand, text)
    competitors = _competitor_names(audit)
    return _persist_items(items, result=result, brand=brand, competitors=competitors)


def _persist_items(items: list[dict], *, result, brand: str, competitors: list[str]) -> List[Claim]:
    out: list[Claim] = []
    for item in items:
        subject = (item.get("subject") or "").strip()
        predicate = (item.get("predicate") or "").strip()
        obj = (item.get("object") or "").strip()
        text_field = (item.get("text") or "").strip() or f"{subject} {predicate} {obj}".strip()
        try:
            confidence = float(item.get("confidence") or 0.5)
        except Exception:
            confidence = 0.5
        if not text_field:
            continue
        if not _is_brand_subject(subject or text_field, brand, competitors):
            continue
        claim = Claim.objects.create(
            result=result,
            audit=result.audit,
            website=result.audit.website,
            text=text_field[:4000],
            subject=subject[:300],
            predicate=predicate[:200],
            object=obj,
            confidence=max(0.0, min(1.0, confidence)),
        )
        try:
            claim.embedding = embed_text(f"{subject} {predicate} {obj}")
            claim.save(update_fields=["embedding", "updated_at"])
        except Exception:
            pass
        out.append(claim)
    return out


def persist_extracted_items(items: list[dict], *, result, brand: str = "", competitors=None):
    """Test/manual hook — persist pre-parsed items without an LLM call."""
    return _persist_items(items, result=result, brand=brand or "", competitors=competitors or [])
