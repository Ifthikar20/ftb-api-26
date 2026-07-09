"""SERP source client — reuses the existing Google CSE wrapper."""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")


def search(query: str, *, num: int = 10) -> list[dict]:
    """Return SERP results for ``query``.

    Each row: ``{url, title, snippet, domain, serp_rank}``. Empty list on
    missing config, quota block, or upstream failure.
    """
    try:
        from apps.llm_ranking.services import google_search
        return google_search.search(query, num=num)
    except Exception as exc:
        logger.warning("SERP search failed for %r: %s", query, exc)
        return []
