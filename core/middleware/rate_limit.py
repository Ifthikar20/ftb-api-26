import logging
import time

from django.core.cache import cache
from django.http import JsonResponse

security_logger = logging.getLogger("security")

# Rate limit tiers — requests per window
RATE_LIMITS = {
    "default": {"requests": 120, "window": 60},       # 120/min for normal browsing
    "api": {"requests": 60, "window": 60},             # 60/min for API calls
    "auth": {"requests": 5, "window": 60},             # 5/min for login attempts
    "sensitive": {"requests": 10, "window": 60},       # 10/min for password resets, etc.
}

# Path prefix → tier mapping
PATH_TIERS = {
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/register": "auth",
    "/api/v1/auth/forgot-password": "sensitive",
    "/api/v1/auth/reset-password": "sensitive",
    "/api/v1/agents/": "api",
    "/api/v1/strategy/": "api",
    "/api/v1/audits/": "api",
    "/api/v1/analytics/": "api",
    "/api/v1/track/": "default",  # pixel ingest has its own DRF throttle
}

# Paths exempt from rate limiting
EXEMPT_PATHS = ["/health/", "/admin/", "/__debug__/", "/api/schema/"]


class AdaptiveRateLimitMiddleware:
    """
    Middleware-level rate limiting based on IP + path tier.
    - Different limits for auth, API, and general endpoints
    - Blocks with 429 + calming message
    - Auto-escalates: repeated violations shorten the cooldown window
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip exempt paths
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        ip = self._get_client_ip(request)
        tier = self._get_tier(request.path)
        limit_config = RATE_LIMITS.get(tier, RATE_LIMITS["default"])

        cache_key = f"rl:{tier}:{ip}"
        violation_key = f"rl:violations:{ip}"

        # Check current count
        current = cache.get(cache_key, 0)

        # Check if this IP has a history of violations (adaptive escalation)
        violations = cache.get(violation_key, 0)
        effective_limit = max(limit_config["requests"] // (1 + violations), 3)

        if current >= effective_limit:
            # Record violation
            cache.set(violation_key, violations + 1, timeout=3600)  # 1hr memory

            security_logger.warning(
                "RATE_LIMITED",
                extra={
                    "ip": ip,
                    "tier": tier,
                    "path": request.path,
                    "count": current,
                    "limit": effective_limit,
                    "violations": violations + 1,
                },
            )

            return JsonResponse(
                {
                    "success": False,
                    "error": {
                        "code": "rate_limited",
                        "message": "You're making requests too quickly. Please wait a moment and try again.",
                    },
                },
                status=429,
                headers={"Retry-After": str(limit_config["window"])},
            )

        # Increment counter
        if current == 0:
            cache.set(cache_key, 1, timeout=limit_config["window"])
        else:
            cache.incr(cache_key)

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Extract the real client IP, respecting proxy headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _get_tier(self, path):
        """Map a request path to its rate limit tier."""
        for prefix, tier in PATH_TIERS.items():
            if path.startswith(prefix):
                return tier
        if path.startswith("/api/"):
            return "api"
        return "default"
