"""Structured audit logger — writes business-significant events to a text log."""

import logging
from typing import Any

audit_logger = logging.getLogger("audit")


def audit_log(
    event: str,
    user=None,
    metadata: dict | None = None,
    level: str = "info",
    request=None,
    action: str = "system",
    resource_type: str = "",
    resource_id: str = "",
    success: bool = True,
    error_message: str = "",
) -> None:
    """
    Emit a structured audit log entry.

    Args:
        event: Dot-notation event name, e.g. "user.login", "billing.checkout_created"
        user: The user performing the action (optional)
        metadata: Additional context (avoid PII unless necessary)
        level: Log level ("info", "warning", "error")
        request: Django request object for extracting IP/UA (optional)
        action: CRUD action type (create/read/update/delete/login/logout/export/api_call/webhook/system)
        resource_type: Type of resource affected, e.g. "subscription", "website"
        resource_id: ID of the affected resource
        success: Whether the operation succeeded
        error_message: Error message if the operation failed
    """
    del action, resource_type, resource_id, success, error_message
    extra: dict[str, Any] = {
        "event": event,
        "metadata": metadata or {},
    }

    if user:
        extra["user_id"] = str(user.id) if hasattr(user, "id") else str(user)
        extra["user_email"] = getattr(user, "email", "")

    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        extra["ip_address"] = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
        extra["request_id"] = getattr(request, "request_id", "")

    log_fn = getattr(audit_logger, level, audit_logger.info)
    log_fn(event, extra=extra)
