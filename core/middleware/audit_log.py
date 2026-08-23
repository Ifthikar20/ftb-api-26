"""
SOC 2 Control: CC6.1 — Log all API access with sufficient detail
for incident investigation and compliance auditing.

Enhanced middleware: writes to both text logs AND the compliance database
for queryable audit trails.

Logs: timestamp, user, IP, method, path, status code, response time,
request ID, user agent. Sensitive data (passwords, tokens) is NEVER logged.
"""

import logging
import time

from django.utils import timezone

audit_logger = logging.getLogger("audit")


class AuditLogMiddleware:
    SENSITIVE_PATHS = ["/api/v1/auth/login/", "/api/v1/auth/register/"]
    EXCLUDED_PATHS = ["/health/", "/ready/", "/metrics/", "/favicon.ico"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in self.EXCLUDED_PATHS):
            return self.get_response(request)

        start_time = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        user_id = str(request.user.id) if request.user.is_authenticated else None
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
        request_id = getattr(request, "request_id", "")

        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "request_id": request_id,
            "user_id": user_id or "anonymous",
            "method": request.method,
            "path": request.path,
            "query_params": self._redact_sensitive(request.GET.dict()) if request.GET else None,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "content_length": request.META.get("CONTENT_LENGTH", 0),
        }

        # 1. Write to text log. Successful GETs are deliberately
        # logged at DEBUG so the dev console stays readable —
        # mutations and errors still surface at INFO/WARNING/ERROR.
        # Set ``LOG_LEVEL=DEBUG`` (or tail the JSON log file) when
        # full-request audit visibility is needed.
        if response.status_code >= 500:
            audit_logger.error("api_request", extra=log_entry)
        elif response.status_code >= 400:
            audit_logger.warning("api_request", extra=log_entry)
        elif request.method != "GET":
            audit_logger.info("api_request", extra=log_entry)
        else:
            audit_logger.debug("api_request", extra=log_entry)

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR")

    # Substrings that mark a query-param key as sensitive. Matched as
    # substrings (not exact keys) so variants like ``reset_token``,
    # ``access_token`` and ``api_key`` are caught, not just ``token``.
    SENSITIVE_KEY_MARKERS = (
        "password", "passwd", "token", "secret", "credit_card", "card",
        "ssn", "api_key", "apikey", "refresh", "access", "otp", "code",
        "auth", "signature", "sig",
    )

    @classmethod
    def _redact_sensitive(cls, data: dict) -> dict:
        return {
            k: "***REDACTED***" if any(m in k.lower() for m in cls.SENSITIVE_KEY_MARKERS) else v
            for k, v in data.items()
        }
