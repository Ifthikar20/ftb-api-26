import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin
from core.mixins.soft_delete_mixin import SoftDeleteMixin
from core.utils.constants import LeadStatus


class Lead(SoftDeleteMixin, TimestampMixin):
    """A lead derived from a visitor's behavior."""

    visitor = models.OneToOneField(
        "analytics.Visitor", on_delete=models.CASCADE, related_name="lead"
    )
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="leads"
    )
    score = models.IntegerField(default=0, db_index=True)
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_leads"
    )
    source = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "leads_lead"
        indexes = [
            models.Index(fields=["website", "score"]),
            models.Index(fields=["website", "status"]),
        ]

    def __str__(self):
        return f"Lead({self.visitor_id}, score={self.score})"


class LeadNote(TimestampMixin):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lead_notes"
    )
    content = models.TextField()

    class Meta:
        db_table = "leads_leadnote"

    def __str__(self):
        return f"Note on Lead({self.lead_id})"


class LeadSegment(TimestampMixin):
    """Saved filter segments for grouping leads."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="lead_segments"
    )
    name = models.CharField(max_length=200)
    rules = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "leads_leadsegment"


class ScoringConfig(TimestampMixin):
    """Per-website lead scoring configuration."""

    website = models.OneToOneField(
        "websites.Website", on_delete=models.CASCADE, related_name="scoring_config"
    )
    weights = models.JSONField(default=dict)
    threshold = models.IntegerField(default=70)
    ml_model_version = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "leads_scoringconfig"

    def __str__(self):
        return f"ScoringConfig({self.website.name})"
