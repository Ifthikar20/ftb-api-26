import json
import time
import logging
from django.utils import timezone

audit_logger = logging.getLogger("audit")


class AuditLogMiddleware:
    """
    SOC2 Control: CC6.1 — Log all API access with sufficient detail
    for incident investigation and compliance auditing.

    Logs: timestamp, user, IP, method, path, status code, response time,
    request ID, user agent. Sensitive data (passwords, tokens) is NEVER logged.
    """

    SENSITIVE_PATHS = ["/api/v1/auth/login/", "/api/v1/auth/register/"]
    EXCLUDED_PATHS = ["/health/", "/ready/", "/metrics/"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in self.EXCLUDED_PATHS):
            return self.get_response(request)

        start_time = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        user_id = str(request.user.id) if request.user.is_authenticated else "anonymous"

        log_entry = {
            "timestamp": timezone.now().isoformat(),
            "request_id": getattr(request, "request_id", "unknown"),
            "user_id": user_id,
            "method": request.method,
            "path": request.path,
            "query_params": request.GET.dict() if request.GET else None,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "ip_address": self._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            "content_length": request.META.get("CONTENT_LENGTH", 0),
        }

        # NEVER log request body for sensitive endpoints
        if request.path not in self.SENSITIVE_PATHS and request.method in ("POST", "PUT", "PATCH"):
            try:
                body = json.loads(request.body) if request.body else None
                if body:
                    log_entry["request_body"] = self._redact_sensitive(body)
            except (json.JSONDecodeError, UnicodeDecodeError, Exception):
                pass  # Includes RawPostDataException when stream already read

        if response.status_code >= 500:
            audit_logger.error("api_request", extra=log_entry)
        elif response.status_code >= 400:
            audit_logger.warning("api_request", extra=log_entry)
        else:
            audit_logger.info("api_request", extra=log_entry)

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR")

    @staticmethod
    def _redact_sensitive(data: dict) -> dict:
        SENSITIVE_KEYS = {"password", "token", "secret", "credit_card", "ssn", "api_key"}
        return {
            k: "***REDACTED***" if k.lower() in SENSITIVE_KEYS else v
            for k, v in data.items()
        }
