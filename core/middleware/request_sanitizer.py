import re
import logging

security_logger = logging.getLogger("security")

# Patterns that indicate potential injection attacks
INJECTION_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r";\s*(drop|delete|insert|update|select)\s+", re.IGNORECASE),
]


class RequestSanitizerMiddleware:
    """
    Input sanitization middleware. Detects and logs potential injection
    attempts. Does not block by default — that's handled by DRF validators.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._check_query_params(request)
        return self.get_response(request)

    def _check_query_params(self, request):
        for key, value in request.GET.items():
            if self._is_suspicious(value):
                security_logger.warning(
                    "Suspicious query parameter detected",
                    extra={
                        "param": key,
                        "ip": request.META.get("REMOTE_ADDR"),
                        "request_id": getattr(request, "request_id", "unknown"),
                    },
                )

    def _is_suspicious(self, value: str) -> bool:
        return any(pattern.search(value) for pattern in INJECTION_PATTERNS)
