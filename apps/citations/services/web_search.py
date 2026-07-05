"""
Perplexity Search API client for Source Intelligence scans.

Returns ranked whole-web results from Perplexity's own index, which is
one of the AI-era engines the product tracks. Follows the module-level
client conventions of apps/llm_ranking/services/google_search.py:
is_configured() guard, per-user daily quota, circuit breaker, narrow
exception handling, empty-list on failure.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from django.conf import settings

from core.quota import DailyQuota
from core.resilience.circuit_breaker import CircuitBreaker

logger = logging.getLogger("apps")

SEARCH_ENDPOINT = "https://api.perplexity.ai/search"
DEFAULT_MAX_RESULTS = 10
DEFAULT_DAILY_LIMIT_PER_USER = 200

_breaker = CircuitBreaker(name="perplexity_search", failure_threshold=5, recovery_timeout=120)

_quota = DailyQuota(
    namespace="pplx_search",
    setting_name="PERPLEXITY_SEARCH_DAILY_LIMIT_PER_USER",
    default_limit=DEFAULT_DAILY_LIMIT_PER_USER,
)


def is_configured() -> bool:
    return bool(getattr(settings, "PERPLEXITY_API_KEY", ""))


def _domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def search_web(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    user_id=None,
    timeout: float = 20.0,
) -> list[dict]:
    """
    Run one Perplexity web search. Returns:

        [{"rank": 1, "url": ..., "domain": ..., "title": ..., "snippet": ...}, ...]

    Returns [] when unconfigured, quota-blocked, breaker-open, or on
    any request failure (logged).
    """
    query = (query or "").strip()
    if not query or not is_configured():
        return []
    if not _breaker.allow():
        logger.warning("Perplexity search breaker open; skipping %r", query)
        return []
    if not _quota.consume(user_id, 1):
        logger.warning("Perplexity search daily quota exhausted for user %s", user_id)
        return []

    try:
        resp = requests.post(
            SEARCH_ENDPOINT,
            json={"query": query, "max_results": max(1, min(int(max_results), 20))},
            headers={
                "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        _breaker.record_success()
    except requests.RequestException as exc:
        _breaker.record_failure()
        logger.warning("Perplexity search failed for %r: %s", query, exc)
        return []
    except ValueError as exc:
        logger.warning("Perplexity search returned non-JSON for %r: %s", query, exc)
        return []

    raw = body.get("results") or body.get("web_results") or []
    results = []
    for idx, item in enumerate(raw[:max_results], start=1):
        url = (item.get("url") or item.get("link") or "").strip()
        if not url:
            continue
        results.append({
            "rank": idx,
            "url": url,
            "domain": _domain(url),
            "title": item.get("title", "") or "",
            "snippet": (item.get("snippet") or item.get("description") or "")[:1000],
            "date": (item.get("date") or "").strip(),
            "last_updated": (item.get("last_updated") or "").strip(),
        })
    return results
