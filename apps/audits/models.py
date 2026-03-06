import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin
from core.utils.constants import AuditStatus, IssueSeverity


class Audit(TimestampMixin):
    """A website audit run."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="audits"
    )
    triggered_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="triggered_audits"
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=AuditStatus.choices, default=AuditStatus.PENDING
    )
    overall_score = models.IntegerField(null=True, blank=True)
    seo_score = models.IntegerField(null=True, blank=True)
    performance_score = models.IntegerField(null=True, blank=True)
    mobile_score = models.IntegerField(null=True, blank=True)
    security_score = models.IntegerField(null=True, blank=True)
    content_score = models.IntegerField(null=True, blank=True)
    report_url = models.URLField(blank=True)
    raw_data = models.JSONField(default=dict)

    class Meta:
        db_table = "audits_audit"
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"Audit({self.website.name}, {self.status})"


class AuditIssue(TimestampMixin):
    """A single issue found during an audit."""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="issues")
    category = models.CharField(max_length=50)  # seo, performance, content, security, mobile
    severity = models.CharField(max_length=20, choices=IssueSeverity.choices)
    title = models.CharField(max_length=300)
    description = models.TextField()
    recommendation = models.TextField()
    resolved = models.BooleanField(default=False)
    element = models.CharField(max_length=500, blank=True)  # Affected element/URL
    impact_score = models.IntegerField(default=0)

    class Meta:
        db_table = "audits_auditissue"
        ordering = ["-impact_score", "severity"]

    def __str__(self):
        return f"Issue({self.severity}: {self.title[:50]})"


class AuditSchedule(models.Model):
    """Automated audit schedule configuration."""

    FREQUENCIES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    website = models.OneToOneField(
        "websites.Website", on_delete=models.CASCADE, related_name="audit_schedule"
    )
    frequency = models.CharField(max_length=20, choices=FREQUENCIES, default="weekly")
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "audits_auditschedule"

    def __str__(self):
        return f"Schedule({self.website.name}, {self.frequency})"
