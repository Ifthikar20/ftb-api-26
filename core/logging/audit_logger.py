import logging
from typing import Any

audit_logger = logging.getLogger("audit")


def audit_log(
    event: str,
    user=None,
    metadata: dict | None = None,
    level: str = "info",
) -> None:
    """
    Emit a structured audit log entry. Used throughout the service layer
    to record business-significant events for SOC 2 compliance.

    Args:
        event: Dot-notation event name, e.g. "user.login", "website.created"
        user: The user performing the action (optional)
        metadata: Additional context (avoid PII unless necessary)
        level: Log level ("info", "warning", "error")
    """
    extra: dict[str, Any] = {
        "event": event,
        "metadata": metadata or {},
    }

    if user:
        extra["user_id"] = str(user.id) if hasattr(user, "id") else str(user)
        extra["user_email"] = getattr(user, "email", "")

    log_fn = getattr(audit_logger, level, audit_logger.info)
    log_fn(event, extra=extra)
