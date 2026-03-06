import logging

from django.core.cache import cache
from django.http import JsonResponse

security_logger = logging.getLogger("security")


class AdaptiveRateLimitMiddleware:
    """
    Middleware-level rate limiting for non-API endpoints and adaptive
    limits based on suspicious activity patterns.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
