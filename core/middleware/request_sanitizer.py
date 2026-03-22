import logging
import re

from django.http import JsonResponse

security_logger = logging.getLogger("security")

# Patterns that indicate potential injection attacks
INJECTION_PATTERNS = [
    re.compile(r"<script[^>]*>", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r";\s*(drop|delete|insert|update|select)\s+", re.IGNORECASE),
    re.compile(r"union\s+select", re.IGNORECASE),
    re.compile(r"--\s*$", re.IGNORECASE),
    re.compile(r"\bor\b\s+1\s*=\s*1", re.IGNORECASE),
    re.compile(r"'\s*or\s+'", re.IGNORECASE),
    re.compile(r"<iframe", re.IGNORECASE),
    re.compile(r"<object", re.IGNORECASE),
    re.compile(r"<embed", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"document\.(cookie|location|write)", re.IGNORECASE),
    re.compile(r"window\.(location|open)", re.IGNORECASE),
]

# Paths that should never be sanitized (e.g. admin, health)
EXEMPT_PATHS = ["/admin/", "/health/", "/__debug__/"]


class RequestSanitizerMiddleware:
    """
    Input sanitization middleware.
    - Scans query params AND request body for injection patterns
    - BLOCKS suspicious requests with a 400 response
    - Logs all blocked attempts for security audit
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip exempt paths
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        # Check query params
        threat = self._scan_params(request.GET, request)
        if threat:
            return self._block_response(request, threat)

        # Check POST body params (form-encoded)
        if request.method in ("POST", "PUT", "PATCH") and request.content_type == "application/x-www-form-urlencoded":
            threat = self._scan_params(request.POST, request)
            if threat:
                return self._block_response(request, threat)

        return self.get_response(request)

    def _scan_params(self, params, request):
        """Scan a QueryDict for suspicious patterns. Returns threat info or None."""
        for key, value in params.items():
            if self._is_suspicious(value):
                return {"param": key, "value": value[:100]}
        return None

    def _is_suspicious(self, value: str) -> bool:
        return any(pattern.search(value) for pattern in INJECTION_PATTERNS)

    def _block_response(self, request, threat):
        """Block the request and log the attempt."""
        ip = request.META.get("REMOTE_ADDR", "unknown")
        request_id = getattr(request, "request_id", "unknown")

        security_logger.warning(
            "BLOCKED: Suspicious input detected",
            extra={
                "param": threat["param"],
                "value_preview": threat["value"][:50],
                "ip": ip,
                "path": request.path,
                "method": request.method,
                "request_id": request_id,
            },
        )

        return JsonResponse(
            {
                "success": False,
                "error": {
                    "code": "invalid_input",
                    "message": "Your request contained invalid characters and was blocked for security.",
                },
            },
            status=400,
        )
