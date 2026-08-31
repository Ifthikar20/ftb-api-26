import logging

from django.core.cache import cache
from django.http import JsonResponse

security_logger = logging.getLogger("security")

# Rate limit tiers — requests per window
RATE_LIMITS = {
    "default": {"requests": 600, "window": 60},       # 600/min for normal browsing
    "api": {"requests": 300, "window": 60},            # 300/min for API calls
    "auth": {"requests": 20, "window": 60},            # 20/min for login/register
    "sensitive": {"requests": 10, "window": 60},       # 10/min for password resets
}

# Path prefix → tier mapping
PATH_TIERS = {
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/register": "auth",
    "/api/v1/auth/refresh": "default",                 # refresh must NOT count as auth
    "/api/v1/auth/forgot-password": "sensitive",
    "/api/v1/auth/reset-password": "sensitive",
    "/api/v1/analytics/": "api",
    "/api/v1/web-analytics/": "api",
    "/api/v1/track/": "default",  # pixel ingest has its own DRF throttle
}

# Paths exempt from rate limiting
EXEMPT_PATHS = ["/health/", "/admin/", "/__debug__/", "/api/schema/", "/static/", "/media/"]


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
        # Cap violations at 3 so effective limit never drops below 25%
        violations = min(cache.get(violation_key, 0), 3)
        effective_limit = max(limit_config["requests"] // (1 + violations), 10)

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

        # Increment counter. Race-safe: cache.add only sets the key if it
        # doesn't already exist; cache.incr can fail with ValueError when
        # the key expired between get() and incr() — fall back to set in
        # that case so the request isn't blocked by a stale read.
        if cache.add(cache_key, 1, timeout=limit_config["window"]):
            pass
        else:
            try:
                cache.incr(cache_key)
            except ValueError:
                cache.set(cache_key, 1, timeout=limit_config["window"])

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Extract the real client IP for the throttle key, proxy-aware.

        The left-most X-Forwarded-For hop is client-supplied and freely
        spoofable, so keying the throttle on it let an attacker rotate the
        header for a fresh bucket per request. Delegate to the shared
        proxy-aware helper, which trusts only our own proxy hops.
        """
        from core.utils.ua_parser import get_client_ip

        return get_client_ip(request) or "unknown"

    def _get_tier(self, path):
        """Map a request path to its rate limit tier."""
        for prefix, tier in PATH_TIERS.items():
            if path.startswith(prefix):
                return tier
        if path.startswith("/api/"):
            return "api"
        return "default"
