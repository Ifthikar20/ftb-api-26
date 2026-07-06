"""
Brand mention and sentiment extraction for Source Intelligence scans.

Facade over the intelligence service. The actual LLM logic lives in
services/intelligence/logic.py (framework-free, single source of
truth). Two modes:

- INTELLIGENCE_SERVICE_URL set (production): call the internal
  intelligence service over HTTP with a bearer token.
- unset (dev, tests, CI): run the shared logic in-process.

Either way this module keeps its original signatures and return
shapes, and remains the only place that records AITokenUsage cost for
these calls (the service is stateless and just reports usage numbers).
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from core.ai_tracking import record_usage
from services.intelligence import logic as intelligence_logic
from services.intelligence.logic import DEFAULT_MODEL, PROMPT_VERSION  # noqa: F401

logger = logging.getLogger("apps")

SERVICE_TIMEOUT = 90.0


def _service_url() -> str:
    return getattr(settings, "INTELLIGENCE_SERVICE_URL", "") or ""


def _service_post(path: str, payload: dict) -> dict | None:
    """POST to the intelligence service. Returns the envelope or None."""
    try:
        resp = requests.post(
            f"{_service_url().rstrip('/')}{path}",
            json=payload,
            headers={
                "Authorization": f"Bearer {getattr(settings, 'INTELLIGENCE_AUTH_TOKEN', '')}",
            },
            timeout=SERVICE_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Intelligence service call %s failed: %s", path, exc)
        return None


def _record(envelope: dict, *, module: str, website, user) -> None:
    usage = envelope.get("usage")
    if not usage:
        return
    record_usage(
        module=module,
        model_name=envelope.get("model") or DEFAULT_MODEL,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        user=user,
        website=website,
        duration_ms=envelope.get("duration_ms", 0),
        metadata={"prompt_version": envelope.get("prompt_version") or PROMPT_VERSION},
    )


def analyze_content(
    text: str,
    *,
    query: str,
    target_brand: str,
    website=None,
    user=None,
) -> dict:
    """Extract brand sentiment from one result's content.

    Returns {"brands": [...], "target_brand_present": bool,
    "relevant_to_query": bool, "summary": str}
    or {"brands": [], "error": "..."} when unavailable/failed.
    """
    if _service_url():
        envelope = _service_post(
            "/v1/analyze-content",
            {"text": text, "query": query, "target_brand": target_brand or ""},
        )
        if envelope is None:
            return {"brands": [], "error": "intelligence_unavailable"}
    else:
        envelope = intelligence_logic.analyze_content(
            text,
            query=query,
            target_brand=target_brand,
            api_key=getattr(settings, "ANTHROPIC_API_KEY", "") or "",
            model_name=intelligence_logic.resolve_model(
                getattr(settings, "LLM_EXTRACTION_MODEL", "") or ""
            ),
        )

    _record(envelope, module="source_sentiment", website=website, user=user)
    return envelope["result"]


def assess_serp_relevance(
    query: str,
    items: list[dict],
    *,
    website=None,
    user=None,
) -> dict[int, dict]:
    """Judge SERP items against the query in ONE cheap model call.

    Runs before any content fetch so off-topic results cost nothing
    downstream. Returns {rank: {"relevant": bool, "reason": str}}.
    Fails open: on missing key, API error, service outage, or malformed
    output every rank is reported relevant so a scan never dies on the
    gate.
    """
    if _service_url():
        envelope = _service_post(
            "/v1/serp-relevance",
            {
                "query": query,
                "items": [
                    {
                        "rank": int(item["rank"]),
                        "title": item.get("title") or "",
                        "url": item.get("url") or "",
                    }
                    for item in items
                ],
            },
        )
        if envelope is None:
            return {
                int(item["rank"]): {"relevant": True, "reason": ""} for item in items
            }
        _record(envelope, module="source_relevance", website=website, user=user)
        # JSON object keys arrive as strings; the pipeline keys by int rank.
        return {int(k): v for k, v in envelope["result"].items()}

    envelope = intelligence_logic.assess_serp_relevance(
        query,
        items,
        api_key=getattr(settings, "ANTHROPIC_API_KEY", "") or "",
        model_name=intelligence_logic.resolve_model(
            getattr(settings, "LLM_EXTRACTION_MODEL", "") or ""
        ),
    )
    _record(envelope, module="source_relevance", website=website, user=user)
    return envelope["result"]
