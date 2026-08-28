"""Community discovery lane for Brand Research.

The web lane finds pages that rank. This lane finds the threads where actual
people argue about the brands, which is where the sentiment and the issues
come from — and, unlike an article, it is somewhere the user can reply.

Two feeds, deliberately overlapping:

- Reddit's public search endpoint. Free, no key, and it reaches threads that
  never rank on Google.
- Google's ``discussions_and_forums`` block (parsed in ``serp_google``),
  which covers Quora, Stack Exchange and standalone forums that Reddit
  search cannot see, and carries Google's own comment counts.

Discovered threads are ordinary ``SourceScanResult`` rows. Everything
downstream already handles them: ``read_reddit_thread`` pulls the top
comments with their upvote scores, and the extraction prompt is already
written to read ``[+N]`` prefixes as community agreement.
"""

from __future__ import annotations

import logging
import math
import time

from apps.citations.services.url_normalizer import normalize_url

logger = logging.getLogger("apps")

# How many threads to carry into the scan. Each one costs a fetch plus an
# LLM extraction call, and past half a dozen the marginal thread mostly
# repeats what the others said.
MAX_THREADS = 6

# Reddit search returns a lot; rank generously, then cut.
REDDIT_SEARCH_LIMIT = 25

# A thread nobody replied to carries no community signal, whatever its
# upvote count.
MIN_COMMENTS = 2


def _thread_score(score: int, num_comments: int, created_utc: float) -> float:
    """Rank threads by discussion, not popularity.

    Upvotes measure whether people liked the link; comments measure whether
    people talked, and only the talking produces brand mentions and
    sentiment. Both are long-tailed, so both go through log10. Freshness is a
    mild multiplier — a two-year-old thread can still be the canonical
    answer, so it is damped rather than excluded.
    """
    comment_weight = math.log10(max(num_comments, 0) + 1)
    upvote_weight = math.log10(max(score, 0) + 1) * 0.5
    age_days = 0.0
    if created_utc:
        age_days = max(0.0, (time.time() - float(created_utc)) / 86400.0)
    # 1.0 today, ~0.7 at a year, floors at 0.5.
    freshness = max(0.5, 1.0 - math.log10(age_days + 1) / 8.0)
    return (comment_weight + upvote_weight) * freshness


def is_enabled() -> bool:
    from django.conf import settings
    return bool(getattr(settings, "BRAND_RESEARCH_COMMUNITY_ENABLED", True))


def discover_reddit(query: str, *, limit: int = MAX_THREADS) -> list[dict]:
    """Search Reddit for threads about ``query``.

    Reuses the Brand Security Reddit client rather than adding a second one.
    Returns [] on any failure — this lane is additive, and a Reddit outage
    must not fail the scan.
    """
    query = (query or "").strip()
    if not query or not is_enabled():
        return []

    try:
        from apps.brand_vault.services.security.sources import reddit
        posts = reddit.search_mentions(query, limit=REDDIT_SEARCH_LIMIT)
    except Exception as exc:
        logger.warning("community: reddit search failed for %r: %s", query, exc)
        return []

    scored = []
    for post in posts or []:
        url = (post.get("url") or "").strip()
        normalized, host, _ = normalize_url(url)
        if not normalized or not host:
            continue
        # Reddit search returns link posts pointing off-site; those are just
        # web pages and belong to the other lane. Keep only real threads.
        if "reddit.com" not in host:
            continue
        num_comments = int(post.get("num_comments") or 0)
        if num_comments < MIN_COMMENTS:
            continue
        score = int(post.get("score") or 0)
        created = float(post.get("created_utc") or 0)
        scored.append((
            _thread_score(score, num_comments, created),
            {
                "url": url,
                "domain": host[4:] if host.startswith("www.") else host,
                "title": (post.get("title") or "")[:500],
                "snippet": (post.get("snippet") or "")[:1000],
                "platform_meta": {
                    "subreddit": post.get("subreddit") or "",
                    "score": score,
                    "num_comments": num_comments,
                    "created_utc": created,
                },
            },
        ))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    rows = []
    for rank, (_, row) in enumerate(scored[:limit], start=1):
        row["rank"] = rank
        rows.append(row)
    return rows


def from_serp_discussions(discussions: list[dict], *, limit: int = MAX_THREADS) -> list[dict]:
    """Normalize ``serp_google``'s discussions block into community rows."""
    rows = []
    for item in (discussions or [])[:limit]:
        url = (item.get("url") or "").strip()
        normalized, host, _ = normalize_url(url)
        if not normalized or not host:
            continue
        rows.append({
            "rank": len(rows) + 1,
            "url": url,
            "domain": item.get("domain") or (host[4:] if host.startswith("www.") else host),
            "title": item.get("title") or "",
            "snippet": item.get("snippet") or "",
            "date": item.get("date") or "",
            "platform_meta": {
                "num_comments": int(item.get("comment_count") or 0),
                "source_label": item.get("source_label") or "",
            },
        })
    return rows
