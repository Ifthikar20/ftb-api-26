"""
Compliance Celery tasks — async audit log writing and retention cleanup.

Tasks:
    1. write_audit_log — async DB write (decoupled from request lifecycle)
    2. cleanup_old_audit_logs — 24-month retention, run weekly
"""

import logging

from celery import shared_task

logger = logging.getLogger("audit")


@shared_task(name="apps.compliance.tasks.write_audit_log", ignore_result=True, max_retries=2)
def write_audit_log(**kwargs):
    """
    Async write of an audit log entry to the database.

    Called from audit_logger.py to decouple DB writes from request processing.
    Falls back gracefully if the DB write fails — the text log is always written first.
    """
    from apps.compliance.models import AuditLog

    try:
        AuditLog.objects.create(**kwargs)
    except Exception as e:
        logger.error(f"Failed to write audit log to DB: {e}", extra=kwargs)


@shared_task(name="apps.compliance.tasks.cleanup_old_audit_logs")
def cleanup_old_audit_logs():
    """
    Purge audit log records older than 24 months.
    Run weekly via Celery Beat.

    Retention period aligns with:
        - SOC 2 Type II (minimum 12 months)
        - GDPR (data minimization principle)
        - Internal policy (24 months for investigation buffer)
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.compliance.models import AuditLog

    cutoff = timezone.now() - timedelta(days=730)  # 24 months
    deleted_count, _ = AuditLog.objects.filter(timestamp__lt=cutoff).delete()
    logger.info(f"Compliance cleanup: purged {deleted_count} audit log records older than 24 months")
