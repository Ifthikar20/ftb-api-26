"""Reddit source client — searches for brand-term mentions across all subs."""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")

USER_AGENT = "cansee-brand-security/0.1"


def search_mentions(query: str, *, limit: int = 25) -> list[dict]:
    """Search Reddit for posts matching ``query``.

    Each row: ``{title, snippet, url, subreddit, score, num_comments, created_utc}``.
    Uses Reddit's public search endpoint. Returns [] on any failure.
    """
    query = (query or "").strip()
    if not query:
        return []
    try:
        import requests
    except ImportError:  # pragma: no cover
        return []
    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={
                "q": query,
                "sort": "new",
                "limit": max(1, min(int(limit), 100)),
                "restrict_sr": "false",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Reddit search failed for %r: %s", query, exc)
        return []
    if resp.status_code != 200:
        logger.warning("Reddit search %r -> HTTP %s", query, resp.status_code)
        return []
    try:
        payload = resp.json()
    except ValueError:
        return []

    out: list[dict] = []
    for child in payload.get("data", {}).get("children", []) or []:
        d = child.get("data") or {}
        title = (d.get("title") or "").strip()
        if not title:
            continue
        selftext = (d.get("selftext") or "").strip()
        permalink = d.get("permalink") or ""
        url = f"https://www.reddit.com{permalink}" if permalink else (d.get("url") or "")
        out.append({
            "title": title,
            "snippet": selftext[:600],
            "url": url,
            "subreddit": d.get("subreddit") or "",
            "score": int(d.get("score") or 0),
            "num_comments": int(d.get("num_comments") or 0),
            "created_utc": float(d.get("created_utc") or 0),
        })
    return out
