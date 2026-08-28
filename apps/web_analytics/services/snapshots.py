"""
Read-through Redis snapshot cache for external traffic sources.

The dashboard polls every ~30s; upstream (GA4 / Cloudflare) is called
at most once per TTL per website regardless of viewer count, and only
while someone is actually looking. Modeled on
apps/metering/services/usage_reader.py with the single-flight lock from
apps/metering/tasks.py.

Nothing here (or anywhere in this app) writes analytics rows to
Postgres — the cache IS the store. Prod Redis runs allkeys-lru, so
every entry is treated as evictable: a lost key just means one extra
upstream fetch.
"""

from __future__ import annotations

import logging

from django.core.cache import cache

logger = logging.getLogger("apps")

# How long the previous good snapshot is kept as a stale fallback.
LAST_TTL_SECONDS = 600


def _keys(kind: str, website_id) -> tuple[str, str, str]:
    base = f"wa:{kind}:{website_id}"
    return base, f"{base}:last", f"{base}:lock"


def get_or_fetch(kind: str, website_id, fetch_fn, *, ttl: int, lock_ttl: int = 10) -> dict:
    """Return the cached snapshot, fetching through on a miss.

    - Fresh hit: returned as-is (carries stale=False).
    - Miss + lock won: fetch_fn() runs inline. A dict result is cached
      for ttl and mirrored into a longer-lived ":last" fallback copy.
    - Miss + lock held elsewhere, or fetch_fn returned None: the last
      good snapshot is served with stale=True, else {"pending": True}.

    Never raises on cache trouble — a broken cache degrades to calling
    fetch_fn directly.
    """
    key, last_key, lock_key = _keys(kind, website_id)

    try:
        cached = cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    won_lock = True
    try:
        won_lock = cache.add(lock_key, 1, lock_ttl)
    except Exception:
        pass

    payload = None
    if won_lock:
        try:
            payload = fetch_fn()
        except Exception as exc:
            logger.warning("web_analytics %s fetch failed for %s: %s", kind, website_id, exc)
            payload = None
        finally:
            try:
                cache.delete(lock_key)
            except Exception:
                pass

    if payload is not None:
        payload = {**payload, "stale": False}
        try:
            cache.set(key, payload, ttl)
            cache.set(last_key, {**payload, "stale": True}, LAST_TTL_SECONDS)
        except Exception:
            pass
        return payload

    try:
        last = cache.get(last_key)
    except Exception:
        last = None
    if last is not None:
        return last
    return {"pending": True, "stale": True}


def invalidate(kind: str, website_id) -> None:
    """Drop cached snapshots for a website (used on disconnect)."""
    key, last_key, _lock = _keys(kind, website_id)
    try:
        cache.delete_many([key, last_key])
    except Exception:
        pass
