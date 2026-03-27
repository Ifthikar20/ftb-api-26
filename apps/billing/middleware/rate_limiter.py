"""
Rate limiting middleware for the Stripe webhook endpoint.

Uses a token bucket algorithm per IP address.
Limits: 100 requests per minute per IP.
Returns 429 Too Many Requests when exceeded — Stripe will retry with backoff.
"""

import logging
import threading
import time

from django.http import JsonResponse

logger = logging.getLogger("billing")


class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max burst
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


class WebhookRateLimitMiddleware:
    """
    Django middleware that rate-limits only the webhook endpoint.

    Config:
        WEBHOOK_RATE_LIMIT_PER_MINUTE: int (default 100)
        WEBHOOK_PATH: str (default '/api/v1/billing/webhook/')
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = threading.Lock()
        self.webhook_path = "/api/v1/billing/webhook/"
        self.rate_per_minute = 100
        self.rate_per_second = self.rate_per_minute / 60
        self._last_cleanup = time.time()

    def _get_client_ip(self, request) -> str:
        """Extract client IP, respecting X-Forwarded-For from reverse proxies."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _cleanup_stale_buckets(self):
        """Prune buckets not seen in the last 5 minutes to prevent memory leak."""
        now = time.time()
        if now - self._last_cleanup < 300:
            return
        with self.lock:
            stale_keys = [
                ip for ip, bucket in self.buckets.items()
                if now - bucket.last_refill > 300
            ]
            for key in stale_keys:
                del self.buckets[key]
            self._last_cleanup = now

    def __call__(self, request):
        # Only rate-limit the webhook endpoint
        if request.path != self.webhook_path:
            return self.get_response(request)

        client_ip = self._get_client_ip(request)

        with self.lock:
            if client_ip not in self.buckets:
                self.buckets[client_ip] = TokenBucket(
                    rate=self.rate_per_second,
                    capacity=self.rate_per_minute,
                )

        bucket = self.buckets[client_ip]

        if not bucket.consume():
            logger.warning(f"Webhook rate limit exceeded for IP: {client_ip}")
            return JsonResponse(
                {"error": "Rate limit exceeded. Please retry later."},
                status=429,
                headers={"Retry-After": "60"},
            )

        self._cleanup_stale_buckets()
        return self.get_response(request)
