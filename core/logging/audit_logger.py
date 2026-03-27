"""
Enhanced audit logger — dual storage (text logs + database).

This module provides the `audit_log()` function used throughout the service
layer to record business-significant events. It writes to:
    1. Text log file (synchronous, immediate — always succeeds)
    2. Database via Celery task (async, queryable — for compliance dashboards)

SOC 2 Control: CC6.1 — Log business-significant events with sufficient detail
for incident investigation and compliance auditing.

Usage:
    from core.logging.audit_logger import audit_log

    audit_log("user.login", user=request.user, metadata={"method": "password"})
    audit_log("billing.checkout_created", user=user, metadata={"plan": "individual"})
"""

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
    extra: dict[str, Any] = {
        "event": event,
        "metadata": metadata or {},
    }

    user_id = None
    user_email = ""
    ip_address = None
    user_agent = ""
    request_id = ""

    if user:
        user_id = str(user.id) if hasattr(user, "id") else str(user)
        user_email = getattr(user, "email", "")
        extra["user_id"] = user_id
        extra["user_email"] = user_email

    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
        request_id = getattr(request, "request_id", "")
        extra["ip_address"] = ip_address
        extra["request_id"] = request_id

    # 1. Always write to text log (synchronous, fast)
    log_fn = getattr(audit_logger, level, audit_logger.info)
    log_fn(event, extra=extra)

    # 2. Write to database via Celery (async, queryable)
    try:
        from apps.compliance.tasks import write_audit_log

        db_kwargs = {
            "event": event,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else "",
            "metadata": metadata or {},
            "success": success,
            "error_message": error_message,
        }

        if user_id:
            db_kwargs["user_id"] = user_id
        if user_email:
            db_kwargs["user_email"] = user_email
        if ip_address:
            db_kwargs["ip_address"] = ip_address
        if user_agent:
            db_kwargs["user_agent"] = user_agent
        if request_id:
            db_kwargs["request_id"] = request_id

        write_audit_log.delay(**db_kwargs)
    except Exception:
        # Never let audit logging break the application
        pass
