"""Google Trends source client — reads rising related queries via SerpAPI.

We use SerpAPI's ``google_trends`` engine because the SerpAPI key is already
configured. If the key is missing this returns [] so the Narrative Watch
agent skips the Trends dimension cleanly.
"""
from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger("apps")

_ENDPOINT = "https://serpapi.com/search.json"


def rising_related(term: str) -> list[dict]:
    """Return rising related queries for ``term``.

    Each row: ``{query, value, link}``. ``value`` is SerpAPI's spike score
    ('Breakout' or a percentage int like 1400). We upcast 'Breakout' to
    10_000 for downstream sorting.
    """
    api_key = getattr(settings, "SERPAPI_KEY", "") or ""
    term = (term or "").strip()
    if not api_key or not term:
        return []
    try:
        import requests
    except ImportError:  # pragma: no cover
        return []
    try:
        resp = requests.get(
            _ENDPOINT,
            params={
                "engine": "google_trends",
                "q": term,
                "data_type": "RELATED_QUERIES",
                "api_key": api_key,
            },
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Trends call failed for %r: %s", term, exc)
        return []
    if resp.status_code != 200:
        logger.warning("Trends %r -> HTTP %s", term, resp.status_code)
        return []
    try:
        payload = resp.json()
    except ValueError:
        return []

    rising = (payload.get("related_queries") or {}).get("rising") or []
    out: list[dict] = []
    for row in rising:
        raw_value = row.get("value")
        if isinstance(raw_value, str) and raw_value.lower().startswith("breakout"):
            value = 10_000
        else:
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                continue
        out.append({
            "query": row.get("query") or "",
            "value": value,
            "link": row.get("link") or "",
        })
    return out
