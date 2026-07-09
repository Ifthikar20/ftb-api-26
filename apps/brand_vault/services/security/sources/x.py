"""X / Twitter source client — recent-search API v2.

Gated on ``settings.FEATURE_X_SCANNER`` and a ``TWITTER_BEARER_TOKEN``.
When either is missing the client returns [] so agents skip X cleanly and
the UI shows the source as "not configured".
"""
from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger("apps")

_RECENT_SEARCH = "https://api.twitter.com/2/tweets/search/recent"


def is_configured() -> bool:
    return (
        bool(getattr(settings, "FEATURE_X_SCANNER", False))
        and bool(getattr(settings, "TWITTER_BEARER_TOKEN", "") or "")
    )


def search_mentions(query: str, *, limit: int = 25) -> list[dict]:
    """Return recent tweets matching ``query``.

    Each row: ``{title, snippet, url, author_id, created_at}``. Empty
    result if the feature flag is off or the API errs.
    """
    if not is_configured():
        return []
    query = (query or "").strip()
    if not query:
        return []
    try:
        import requests
    except ImportError:  # pragma: no cover
        return []
    token = getattr(settings, "TWITTER_BEARER_TOKEN", "")
    try:
        resp = requests.get(
            _RECENT_SEARCH,
            params={
                "query": query,
                "max_results": max(10, min(int(limit), 100)),
                "tweet.fields": "created_at,author_id,public_metrics",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("X search failed for %r: %s", query, exc)
        return []
    if resp.status_code != 200:
        logger.warning("X search %r -> HTTP %s", query, resp.status_code)
        return []
    try:
        payload = resp.json()
    except ValueError:
        return []

    out: list[dict] = []
    for tweet in payload.get("data") or []:
        tid = tweet.get("id") or ""
        text = (tweet.get("text") or "").strip()
        if not tid or not text:
            continue
        out.append({
            "title": text[:140],
            "snippet": text[:600],
            "url": f"https://x.com/i/status/{tid}",
            "author_id": tweet.get("author_id") or "",
            "created_at": tweet.get("created_at") or "",
        })
    return out
