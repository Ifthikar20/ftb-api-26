"""Live Google search lookup for a generated prompt.

Surfaces "where this question is being asked from" — top 5-10 organic results
on Google for the prompt text, classified by source domain (Reddit, Quora,
news, blog, etc.). Used to power the "Found in" panel inside the Prompt
Library expand drawer.

Falls back gracefully when SERPAPI_KEY is missing so dev environments still
work; the frontend renders an explanatory empty state in that case.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger("apps")


_SOURCE_RULES: list[tuple[str, str]] = [
    (r"(^|\.)reddit\.com$", "reddit"),
    (r"(^|\.)quora\.com$", "quora"),
    (r"(^|\.)stackexchange\.com$", "stackoverflow"),
    (r"(^|\.)stackoverflow\.com$", "stackoverflow"),
    (r"(^|\.)wikipedia\.org$", "wikipedia"),
    (r"(^|\.)youtube\.com$", "youtube"),
    (r"(^|\.)twitter\.com$", "social"),
    (r"(^|\.)x\.com$", "social"),
    (r"(^|\.)linkedin\.com$", "social"),
    (r"(^|\.)facebook\.com$", "social"),
    (r"(^|\.)instagram\.com$", "social"),
    (r"(^|\.)tiktok\.com$", "social"),
    (r"(^|\.)yelp\.com$", "review"),
    (r"(^|\.)tripadvisor\.com$", "review"),
    (r"(^|\.)trustpilot\.com$", "review"),
    (r"(^|\.)g2\.com$", "review"),
    (r"(^|\.)nytimes\.com$", "news"),
    (r"(^|\.)bbc\.com$", "news"),
    (r"(^|\.)theguardian\.com$", "news"),
    (r"(^|\.)techcrunch\.com$", "news"),
    (r"(^|\.)bloomberg\.com$", "news"),
    (r"(^|\.)forbes\.com$", "news"),
    (r"(^|\.)medium\.com$", "blog"),
    (r"(^|\.)substack\.com$", "blog"),
    (r"(^|\.)gov$", "gov"),
    (r"(^|\.)edu$", "edu"),
]


def _classify_domain(host: str) -> str:
    h = (host or "").lower().lstrip("www.")
    for pat, label in _SOURCE_RULES:
        if re.search(pat, h):
            return label
    return "other"


def _row(item: dict, position: int) -> dict | None:
    title = (item.get("title") or "").strip()
    link = (item.get("link") or "").strip()
    if not title or not link:
        return None
    try:
        host = urlparse(link).hostname or ""
    except Exception:
        host = ""
    return {
        "title": title,
        "url": link,
        "domain": host,
        "snippet": (item.get("snippet") or "").strip()[:280],
        "position": position,
        "source_class": _classify_domain(host),
    }


def search_sources(query: str, *, limit: int = 8) -> dict[str, Any]:
    """Return ``{provider, results, query}``. ``results`` is a list of dicts
    with title/url/domain/snippet/source_class. Empty when SerpAPI isn't
    configured or the call fails — caller should treat that as a graceful
    'no data yet' state, NOT an error to bubble up."""
    query = (query or "").strip()
    if not query:
        return {"provider": "fallback", "results": [], "query": query}

    api_key = getattr(settings, "SERPAPI_KEY", "")
    if not api_key:
        return {"provider": "unconfigured", "results": [], "query": query}

    try:
        import requests
    except ImportError:  # pragma: no cover
        return {"provider": "unconfigured", "results": [], "query": query}

    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={
                "q": query[:500],
                "engine": "google",
                "num": str(max(5, min(limit, 10))),
                "api_key": api_key,
            },
            timeout=12,
        )
    except Exception as exc:
        logger.warning("search_sources network error: %s", exc)
        return {"provider": "serpapi", "results": [], "query": query, "error": "network"}

    if resp.status_code != 200:
        logger.warning("search_sources non-200: %s", resp.status_code)
        return {"provider": "serpapi", "results": [], "query": query, "error": f"http_{resp.status_code}"}

    try:
        data = resp.json()
    except Exception:
        return {"provider": "serpapi", "results": [], "query": query, "error": "decode"}

    organic = data.get("organic_results") or []
    rows: list[dict] = []
    for i, item in enumerate(organic[:limit], start=1):
        row = _row(item, i)
        if row is not None:
            rows.append(row)
    return {"provider": "serpapi", "results": rows, "query": query}
