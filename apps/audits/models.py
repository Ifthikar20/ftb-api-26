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


class SEOGraderIssue(TimestampMixin):
    """Per-page SEO issue with original value and suggested fix."""

    CATEGORIES = [
        ("page_title", "Page Title"),
        ("meta_description", "Meta Description"),
        ("image_alt", "Image Alt Text"),
        ("h1_length", "H1 Length"),
        ("h2_length", "H2 Length"),
        ("heading_optimization", "Heading Optimizations"),
        ("canonical_link", "Canonical Link"),
        ("og_title", "OG Title"),
        ("og_description", "OG Description"),
        ("og_url", "OG URL"),
        ("twitter_title", "Twitter Title"),
        ("twitter_description", "Twitter Description"),
        ("twitter_site", "Twitter Site"),
        ("twitter_card", "Twitter Card"),
        ("lang_missing", "Lang Missing"),
        ("meta_keywords", "Meta Keywords"),
        ("internal_linking", "Internal Linking Suggestions"),
        ("organization_schema", "Organization Schema"),
        ("missing_keywords", "Missing Keywords"),
        ("link_issues", "Issues with Links"),
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="grader_issues")
    category = models.CharField(max_length=50)
    page_url = models.CharField(max_length=500)
    original_value = models.TextField(blank=True, default="")
    original_length = models.IntegerField(default=0)
    suggested_fix = models.TextField(blank=True, default="")
    suggested_length = models.IntegerField(default=0)
    deployed = models.BooleanField(default=False)

    class Meta:
        db_table = "audits_seograderissue"
        ordering = ["category", "page_url"]

    def __str__(self):
        return f"GraderIssue({self.category}: {self.page_url[:40]})"


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
