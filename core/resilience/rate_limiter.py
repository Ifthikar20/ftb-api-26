"""
Redis-backed token-bucket rate limiter for outbound API calls.

One bucket per upstream dependency (e.g. one per LLM provider). Keeps a single
counter and last-refill timestamp so multiple workers and web processes share
the same budget without coordinating.

If Redis is unreachable the limiter fails open (allows the call) — same
pattern as CircuitBreaker, since a cache outage must not take down the
caller.

Usage:
    bucket = TokenBucket(name="llm:claude", capacity=20, refill_per_second=20/60)
    if not bucket.try_acquire():
        raise RateLimited("claude")
    result = call_claude()
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("core.resilience")


class RateLimited(Exception):
    """Raised when a token-bucket bucket is empty."""

    def __init__(self, name: str):
        super().__init__(f"Rate limit exceeded for [{name}]")
        self.name = name


class TokenBucket:
    """
    Redis-backed token bucket.

    capacity: maximum tokens the bucket holds (burst size)
    refill_per_second: tokens added per second (steady-state rate)
    """

    def __init__(self, name: str, *, capacity: int, refill_per_second: float) -> None:
        self.name = name
        self.capacity = capacity
        self.refill_per_second = refill_per_second

    @property
    def _key(self) -> str:
        return f"rl:{self.name}"

    def _redis(self):
        try:
            from django.core.cache import cache
            return cache
        except Exception:
            return None

    def try_acquire(self, n: int = 1) -> bool:
        """
        Reserve n tokens if available. Returns True on success, False when
        the bucket is empty. Refills tokens lazily based on time elapsed
        since the last call.
        """
        cache = self._redis()
        if cache is None:
            return True  # fail open

        now = time.time()
        try:
            stored = cache.get(self._key)
            if stored is None:
                tokens = float(self.capacity)
                last_refill = now
            else:
                tokens, last_refill = stored
                tokens = float(tokens)
                last_refill = float(last_refill)

            elapsed = max(0.0, now - last_refill)
            tokens = min(self.capacity, tokens + elapsed * self.refill_per_second)

            if tokens < n:
                # Persist the refilled state so future calls see it.
                cache.set(self._key, (tokens, now), timeout=300)
                return False

            tokens -= n
            cache.set(self._key, (tokens, now), timeout=300)
            return True
        except Exception as exc:
            logger.warning("TokenBucket[%s] cache failure (failing open): %s", self.name, exc)
            return True
