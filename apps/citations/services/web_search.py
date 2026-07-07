"""
Perplexity Search API client for Source Intelligence scans.

Facade over the sources service. The actual search client lives in
services/sources/logic.py (framework-free, single source of truth).
Two modes:

- SOURCES_SERVICE_URL set (production): call the internal sources
  service over HTTP with a bearer token.
- unset (dev, tests, CI): run the shared logic in-process.

Stateful guards stay HERE in both modes: the per-user daily quota and
the circuit breaker are Django-side concerns (cache/Redis backed), so
the service remains stateless.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from core.quota import DailyQuota
from core.resilience.circuit_breaker import CircuitBreaker
from services.sources import logic as sources_logic
from services.sources.logic import DEFAULT_MAX_RESULTS, SEARCH_ENDPOINT  # noqa: F401

logger = logging.getLogger("apps")

DEFAULT_DAILY_LIMIT_PER_USER = 200

_breaker = CircuitBreaker(name="perplexity_search", failure_threshold=5, recovery_timeout=120)

_quota = DailyQuota(
    namespace="pplx_search",
    setting_name="PERPLEXITY_SEARCH_DAILY_LIMIT_PER_USER",
    default_limit=DEFAULT_DAILY_LIMIT_PER_USER,
)


def is_configured() -> bool:
    # Configured means either the key is local (in-process mode) or the
    # sources service owns the key (HTTP mode).
    return bool(
        getattr(settings, "PERPLEXITY_API_KEY", "")
        or getattr(settings, "SOURCES_SERVICE_URL", "")
    )


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

    service_url = getattr(settings, "SOURCES_SERVICE_URL", "") or ""
    if service_url:
        try:
            resp = requests.post(
                f"{service_url.rstrip('/')}/v1/search",
                json={"query": query, "max_results": max_results, "timeout": timeout},
                headers={
                    "Authorization": f"Bearer {getattr(settings, 'SOURCES_AUTH_TOKEN', '')}",
                },
                timeout=timeout + 5,
            )
            resp.raise_for_status()
            body = resp.json()
        except (requests.RequestException, ValueError) as exc:
            _breaker.record_failure()
            logger.warning("Sources service search failed for %r: %s", query, exc)
            return []
        _breaker.record_success()
        return body.get("results") or []

    try:
        results = sources_logic.perplexity_search(
            query,
            api_key=settings.PERPLEXITY_API_KEY,
            max_results=max_results,
            timeout=timeout,
        )
    except sources_logic.SearchRequestError as exc:
        _breaker.record_failure()
        logger.warning("Perplexity search failed for %r: %s", query, exc)
        return []
    except sources_logic.SearchParseError as exc:
        logger.warning("Perplexity search returned non-JSON for %r: %s", query, exc)
        return []
    _breaker.record_success()
    return results


def summarize_url_with_perplexity(
    url: str,
    *,
    query: str,
    user_id: int | None = None,
    timeout: float = 20.0,
) -> dict | None:
    """Ask Perplexity to visit a URL and return a factual summary.

    Used as a fetch-fallback when our direct HTTP reader is blocked
    (Reddit 403, paywalls, anti-bot walls). Returns a content-shaped
    dict {text, word_count} on success, None on any failure. Fails
    silent: this is a best-effort recovery path — the pipeline continues
    normally if it returns None.
    """
    if not _breaker.allow():
        logger.warning("Perplexity summarize breaker open; skipping %s", url)
        return None
    if user_id and not _quota.consume(user_id):
        logger.warning("Perplexity summarize daily quota exhausted for user %s", user_id)
        return None

    service_url = getattr(settings, "SOURCES_SERVICE_URL", "") or ""
    if service_url:
        try:
            resp = requests.post(
                f"{service_url.rstrip('/')}/v1/summarize-url",
                json={"url": url, "query": query, "timeout": timeout},
                headers={
                    "Authorization": f"Bearer {getattr(settings, 'SOURCES_AUTH_TOKEN', '')}",
                },
                timeout=timeout + 5,
            )
            resp.raise_for_status()
            body = resp.json()
        except (requests.RequestException, ValueError) as exc:
            _breaker.record_failure()
            logger.warning("Sources service summarize failed for %s: %s", url, exc)
            return None
        _breaker.record_success()
        return body if body.get("text") else None

    try:
        summary = sources_logic.perplexity_summarize_url(
            url,
            query=query,
            api_key=settings.PERPLEXITY_API_KEY,
            timeout=timeout,
        )
    except sources_logic.SearchRequestError as exc:
        _breaker.record_failure()
        logger.warning("Perplexity summarize failed for %s: %s", url, exc)
        return None
    except sources_logic.SearchParseError as exc:
        logger.warning("Perplexity summarize returned non-JSON for %s: %s", url, exc)
        return None
    _breaker.record_success()
    return summary if summary and summary.get("text") else None
