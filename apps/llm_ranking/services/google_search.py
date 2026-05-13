"""
Google Programmable Search (Custom Search JSON API) client.

Used by the Model Test pipeline to fetch the real publisher URLs that
back a user's prompt — instead of relying on Gemini grounding's
opaque vertexaisearch.cloud.google.com/grounding-api-redirect/... URIs.

Cost guards:
  - 1-hour Django-cache per (query, num) — repeat prompts are free.
  - ``max_queries`` cap on ``search_many`` — bounds worst-case
    spend regardless of how many prompts a user submits.
  - Per-user daily quota (Redis-backed) — refuses CSE calls once the
    user's plan-specific daily limit is exhausted, so a single power
    user can't drain the project budget.

Requires two Django settings:
    GOOGLE_API_KEY  — API key with the Custom Search API enabled
    GOOGLE_CSE_ID   — Programmable Search Engine ID (cx parameter)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps")

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
DEFAULT_NUM = 5         # Google CSE returns up to 10 per call.
DEFAULT_MAX_QUERIES = 15  # Per-run safety cap.
DEFAULT_MAX_TOTAL = 20  # Per-run citation cap.
CACHE_TTL = 60 * 60     # 1h — search results drift but slowly.

# Daily CSE query allowance per user. Single flat number — every user
# gets the same cap, regardless of plan. Resets at UTC midnight.
# Override with GOOGLE_CSE_DAILY_LIMIT_PER_USER in env.
DEFAULT_DAILY_LIMIT_PER_USER = 100


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
        host = urlparse(url).hostname or ""
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


# ── Per-user daily quota ──────────────────────────────────────────────────

def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _quota_key(user_id) -> str:
    return f"gcse:quota:{user_id or 'anon'}:{_today_str()}"


def quota_for_user(user_id) -> int:
    """Daily CSE query allowance. Same flat number for every caller."""
    return int(getattr(
        settings,
        "GOOGLE_CSE_DAILY_LIMIT_PER_USER",
        DEFAULT_DAILY_LIMIT_PER_USER,
    ))


def quota_remaining(user_id) -> int:
    """Calls left for ``user_id`` today. Never negative."""
    used = int(cache.get(_quota_key(user_id)) or 0)
    return max(0, quota_for_user(user_id) - used)


def _consume_quota(user_id, n: int = 1) -> bool:
    """
    Reserve ``n`` calls. Returns False (and doesn't increment) when
    the user would exceed their daily quota.
    """
    key = _quota_key(user_id)
    used = int(cache.get(key) or 0)
    if used + n > quota_for_user(user_id):
        return False
    # 26h TTL covers DST + UTC midnight rollover slack.
    cache.set(key, used + n, timeout=60 * 60 * 26)
    return True


# ── Search ────────────────────────────────────────────────────────────────

def search(
    query: str,
    *,
    num: int = DEFAULT_NUM,
    timeout: float = 6.0,
    user_id=None,
    stats: dict | None = None,
) -> list[dict]:
    """
    Run a single CSE query. Returns a list of dicts:

        [{"url": str, "title": str, "snippet": str, "domain": str}, ...]

    Returns [] when the API isn't configured, the call fails, no
    results, or the user hit their daily quota. Cached per (query, num)
    for an hour.

    Pass a ``stats`` dict to receive accounting back: increments
    'cache_hits', 'api_calls', 'quota_blocks', 'errors' in-place.
    """
    query = (query or "").strip()
    if not query or not is_configured():
        return []

    cached = cache.get(_cache_key(query, num))
    if cached is not None:
        if stats is not None:
            stats["cache_hits"] = stats.get("cache_hits", 0) + 1
        return cached

    if not _consume_quota(user_id, 1):
        if stats is not None:
            stats["quota_blocks"] = stats.get("quota_blocks", 0) + 1
        return []

    params = {
        "key":  settings.GOOGLE_API_KEY,
        "cx":   settings.GOOGLE_CSE_ID,
        "q":    query,
        "num":  max(1, min(int(num), 10)),
        "safe": "off",
    }
    try:
        resp = requests.get(CSE_ENDPOINT, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if stats is not None:
            stats["api_calls"] = stats.get("api_calls", 0) + 1
    except requests.RequestException as exc:
        if stats is not None:
            stats["errors"] = stats.get("errors", 0) + 1
        logger.warning("Google CSE call failed for %r: %s", query, exc)
        return []
    except ValueError as exc:
        if stats is not None:
            stats["errors"] = stats.get("errors", 0) + 1
        logger.warning("Google CSE returned non-JSON for %r: %s", query, exc)
        return []

    items = data.get("items") or []
    results = []
    for idx, item in enumerate(items, start=1):
        url = (item.get("link") or "").strip()
        if not url:
            continue
        results.append({
            "url":       url,
            "title":     item.get("title") or url,
            "snippet":   item.get("snippet") or "",
            "domain":    _domain(url),
            "serp_rank": idx,  # 1-indexed Google organic rank for this query
        })
    cache.set(_cache_key(query, num), results, timeout=CACHE_TTL)
    return results


def search_many(
    queries: list[str],
    *,
    num_per_query: int = DEFAULT_NUM,
    max_total: int = DEFAULT_MAX_TOTAL,
    max_queries: int = DEFAULT_MAX_QUERIES,
    user_id=None,
) -> dict:
    """
    Run several CSE queries and merge the results, deduplicated by
    URL. Bounded by both ``max_queries`` (hard cap on CSE calls) and
    ``max_total`` (hard cap on returned citations).

    Returns an accounting envelope:

        {
            "citations":      [...],   # merged, deduped
            "queries_made":   int,     # CSE calls actually made (cache + API)
            "api_calls":      int,     # uncached calls (i.e. paid calls)
            "cache_hits":     int,
            "errors":         int,
            "quota_blocks":   int,     # # queries we refused this run
            "max_queries":    int,     # the cap that was in effect
            "max_total":      int,
            "capped":         bool,    # True iff we stopped due to a cap
            "quota_exceeded": bool,    # True iff the user ran out of quota mid-run
            "plan":           str,
            "quota_remaining": int,    # for user_id, AFTER this run
        }
    """
    stats = {"cache_hits": 0, "api_calls": 0, "quota_blocks": 0, "errors": 0}
    seen: dict[str, dict] = {}
    queries_made = 0
    capped = False
    quota_exceeded = False

    for q in queries:
        if not q:
            continue
        if queries_made >= max_queries:
            capped = True
            break
        results = search(q, num=num_per_query, user_id=user_id, stats=stats)
        queries_made += 1
        # If the search returned [] AND quota_blocks just ticked, the
        # user ran out mid-run — stop trying so we don't keep hammering
        # the no-op path.
        if not results and stats["quota_blocks"]:
            quota_exceeded = True
            break
        for r in results:
            entry = seen.get(r["url"])
            if entry is None:
                entry = {**r, "queries": [q], "best_serp_rank": r.get("serp_rank")}
                seen[r["url"]] = entry
            else:
                if q not in entry["queries"]:
                    entry["queries"].append(q)
                # Keep the best (lowest) rank we've ever seen this URL at.
                rk = r.get("serp_rank")
                cur = entry.get("best_serp_rank")
                if rk is not None and (cur is None or rk < cur):
                    entry["best_serp_rank"] = rk
            if len(seen) >= max_total:
                capped = True
                break
        if len(seen) >= max_total:
            break

    return {
        "citations":      list(seen.values())[:max_total],
        "queries_made":   queries_made,
        "api_calls":      stats["api_calls"],
        "cache_hits":     stats["cache_hits"],
        "errors":         stats["errors"],
        "quota_blocks":   stats["quota_blocks"],
        "max_queries":    max_queries,
        "max_total":      max_total,
        "capped":         capped,
        "quota_exceeded": quota_exceeded,
        "daily_limit":    quota_for_user(user_id),
        "quota_remaining": quota_remaining(user_id),
    }
