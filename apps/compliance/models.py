"""
Compliance audit logging models.

Provides a queryable, database-backed audit trail for SOC 2, GDPR, and
regulatory compliance. Extends the existing text-based audit logger with
structured, searchable records.

Architecture decisions:
    - Separate app: compliance is a cross-cutting concern, isolated from business logic
    - Write-only by design: records can be created but NEVER updated or deleted via ORM
    - Async writes: uses Celery to avoid performance impact on API requests
    - Dual storage: writes to both database AND structured log files
    - Retention: 24-month retention with automated cleanup task
"""

import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit log record for compliance.

    Each record captures WHO did WHAT, WHEN, WHERE, and the OUTCOME.
    Records are append-only and should never be modified or deleted
    outside of the automated retention cleanup task.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # WHO
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_email = models.CharField(max_length=255, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")

    # WHAT
    event = models.CharField(
        max_length=120,
        db_index=True,
        help_text="Dot-notation event name, e.g. 'user.login', 'billing.checkout_created'",
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ("create", "Create"),
            ("read", "Read"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("login", "Login"),
            ("logout", "Logout"),
            ("export", "Export"),
            ("api_call", "API Call"),
            ("webhook", "Webhook"),
            ("system", "System"),
        ],
        default="api_call",
        db_index=True,
    )
    resource_type = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Type of resource affected, e.g. 'subscription', 'website', 'lead'",
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="ID of the affected resource",
    )

    # WHEN
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # WHERE
    method = models.CharField(max_length=10, blank=True, default="")
    path = models.CharField(max_length=500, blank=True, default="")
    request_id = models.CharField(max_length=50, blank=True, default="")

    # CONTEXT
    status_code = models.IntegerField(null=True, blank=True)
    duration_ms = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context. NEVER include PII, passwords, or sensitive data.",
    )

    # OUTCOME
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "compliance_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user_id", "-timestamp"]),
            models.Index(fields=["event", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["-timestamp", "success"]),
        ]
        # Prevent Django admin from offering delete
        default_permissions = ("add", "view")

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.event} by {self.user_email or 'system'}"

    def save(self, *args, **kwargs):
        # Prevent updates to existing records (immutable audit trail)
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit log records are immutable and cannot be updated.")
        super().save(*args, **kwargs)
