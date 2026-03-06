import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin
from core.utils.constants import ThreatLevel


class Competitor(TimestampMixin):
    """A tracked competitor website."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="competitors"
    )
    competitor_url = models.URLField(max_length=500)
    name = models.CharField(max_length=200, blank=True)
    auto_detected = models.BooleanField(default=False)
    estimated_traffic = models.IntegerField(null=True, blank=True)
    domain_authority = models.IntegerField(null=True, blank=True)
    threat_level = models.CharField(
        max_length=20, choices=ThreatLevel.choices, default=ThreatLevel.LOW
    )
    last_crawled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "competitors_competitor"
        unique_together = [("website", "competitor_url")]

    def __str__(self):
        return f"{self.name or self.competitor_url}"


class CompetitorSnapshot(TimestampMixin):
    """Point-in-time metrics snapshot for a competitor."""

    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name="snapshots")
    captured_at = models.DateTimeField(db_index=True)
    traffic_estimate = models.IntegerField(null=True)
    keyword_count = models.IntegerField(null=True)
    backlink_count = models.IntegerField(null=True)
    content_count = models.IntegerField(null=True)
    metrics = models.JSONField(default=dict)

    class Meta:
        db_table = "competitors_competitorsnapshot"
        ordering = ["-captured_at"]

    def __str__(self):
        return f"Snapshot({self.competitor.name}, {self.captured_at.date()})"


class KeywordGap(TimestampMixin):
    """Keyword gap analysis between user's site and competitors."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="keyword_gaps"
    )
    keyword = models.CharField(max_length=500, db_index=True)
    your_rank = models.IntegerField(null=True, blank=True)
    competitor_ranks = models.JSONField(default=dict)
    search_volume = models.IntegerField(null=True)
    difficulty = models.IntegerField(null=True)
    opportunity_score = models.FloatField(default=0)

    class Meta:
        db_table = "competitors_keywordgap"
        unique_together = [("website", "keyword")]


class CompetitorChange(TimestampMixin):
    """Detected changes in a competitor's website."""

    CHANGE_TYPES = [
        ("new_page", "New Page"),
        ("removed_page", "Removed Page"),
        ("ranking_change", "Ranking Change"),
        ("content_update", "Content Update"),
        ("pricing_change", "Pricing Change"),
    ]

    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name="changes")
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)
    detail = models.JSONField(default=dict)
    detected_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "competitors_competitorchange"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Change({self.change_type} @ {self.competitor.name})"
