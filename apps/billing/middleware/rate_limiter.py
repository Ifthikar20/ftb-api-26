"""
Rate limiting middleware for inbound webhook endpoints (Polar, Slack,
Discord).

Token bucket per endpoint per IP address via the shared Redis-backed
limiter, so the limit holds across every gunicorn worker instead of
multiplying by process count. Limits: 100 requests per minute per IP.
Returns 429 Too Many Requests when exceeded — the senders retry with
backoff.
"""

import logging

from django.http import JsonResponse

from core.resilience import TokenBucket
from core.utils.ua_parser import get_client_ip

logger = logging.getLogger("billing")

# Every unauthenticated inbound-webhook endpoint gets its own bucket.
WEBHOOK_PATHS = {
    "/api/v1/billing/polar/webhook/",
    "/api/v1/notifications/discord/interactions/",
    "/api/v1/notifications/slack/events/",
    "/api/v1/notifications/slack/commands/",
}


class WebhookRateLimitMiddleware:
    """
    Django middleware that rate-limits only the webhook endpoints.

    The client IP comes from core's proxy-aware get_client_ip (reads
    X-Forwarded-For from the right per TRUSTED_PROXY_COUNT), so a caller
    cannot dodge the limit by prepending forged entries. Bucket state
    lives in Redis with a 300s TTL, so idle IPs clean themselves up.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.webhook_paths = set(WEBHOOK_PATHS)
        self.rate_per_minute = 100

    def _bucket_name(self, path: str, client_ip: str) -> str:
        """Per-endpoint bucket name, derived from the path segments
        after /api/v1/."""
        segments = [s for s in path.split("/") if s][2:]
        return "webhook:" + "-".join(segments) + f":{client_ip}"

    def __call__(self, request):
        # Only rate-limit the webhook endpoints
        if request.path not in self.webhook_paths:
            return self.get_response(request)

        client_ip = get_client_ip(request) or "unknown"
        bucket = TokenBucket(
            name=self._bucket_name(request.path, client_ip),
            capacity=self.rate_per_minute,
            refill_per_second=self.rate_per_minute / 60,
        )

        if not bucket.try_acquire():
            logger.warning(f"Webhook rate limit exceeded for IP: {client_ip}")
            return JsonResponse(
                {"error": "Rate limit exceeded. Please retry later."},
                status=429,
                headers={"Retry-After": "60"},
            )

        return self.get_response(request)
