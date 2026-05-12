"""
Google Programmable Search (Custom Search JSON API) client.

Used by the Model Test pipeline to fetch the real publisher URLs that
back a user's prompt — instead of relying on Gemini grounding's
opaque vertexaisearch.cloud.google.com/grounding-api-redirect/... URIs.

Requires two Django settings:
    GOOGLE_API_KEY  — API key with the Custom Search API enabled
    GOOGLE_CSE_ID   — Programmable Search Engine ID (cx parameter)
"""

from __future__ import annotations

import hashlib
import logging
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps")

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
DEFAULT_NUM = 5         # Google CSE returns up to 10 per call.
CACHE_TTL = 60 * 60     # 1h — search results drift but slowly.


def is_configured() -> bool:
    return bool(
        getattr(settings, "GOOGLE_API_KEY", "")
        and getattr(settings, "GOOGLE_CSE_ID", "")
    )


def _cache_key(query: str, num: int) -> str:
    h = hashlib.sha1(f"{query.strip().lower()}|{num}".encode("utf-8")).hexdigest()
    return f"gcse:v1:{h}"


def _domain(url: str) -> str:
    try:
        return urlparse(url).hostname.lstrip("www.")
    except Exception:
        return ""


def search(query: str, *, num: int = DEFAULT_NUM, timeout: float = 6.0) -> list[dict]:
    """
    Run a single CSE query. Returns a list of dicts:

        [{"url": str, "title": str, "snippet": str, "domain": str}, ...]

    Returns [] when the API isn't configured, the call fails, or the
    query returns no results. Cached for an hour per (query, num).
    """
    query = (query or "").strip()
    if not query or not is_configured():
        return []
    cached = cache.get(_cache_key(query, num))
    if cached is not None:
        return cached
    params = {
        "key": settings.GOOGLE_API_KEY,
        "cx":  settings.GOOGLE_CSE_ID,
        "q":   query,
        "num": max(1, min(int(num), 10)),
        "safe": "off",
    }
    try:
        resp = requests.get(CSE_ENDPOINT, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("Google CSE call failed for %r: %s", query, exc)
        return []
    except ValueError as exc:
        logger.warning("Google CSE returned non-JSON for %r: %s", query, exc)
        return []
    items = data.get("items") or []
    results = []
    for item in items:
        url = (item.get("link") or "").strip()
        if not url:
            continue
        results.append({
            "url":     url,
            "title":   item.get("title") or url,
            "snippet": item.get("snippet") or "",
            "domain":  _domain(url),
        })
    cache.set(_cache_key(query, num), results, timeout=CACHE_TTL)
    return results


def search_many(
    queries: list[str],
    *,
    num_per_query: int = DEFAULT_NUM,
    max_total: int = 20,
) -> list[dict]:
    """
    Run several CSE queries and merge the results, deduplicated by URL
    and capped at ``max_total``. Each returned entry adds a ``queries``
    list naming the prompts that surfaced it, so the UI can credit
    which user prompt drove each citation.
    """
    seen: dict[str, dict] = {}
    for q in queries:
        if not q:
            continue
        for r in search(q, num=num_per_query):
            entry = seen.get(r["url"])
            if entry is None:
                entry = {**r, "queries": [q]}
                seen[r["url"]] = entry
            elif q not in entry["queries"]:
                entry["queries"].append(q)
            if len(seen) >= max_total:
                break
        if len(seen) >= max_total:
            break
    return list(seen.values())[:max_total]
