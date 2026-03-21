import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class Visitor(TimestampMixin):
    """A unique visitor tracked by the pixel."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="visitors"
    )
    fingerprint_hash = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True)  # Hashed, not raw IP (privacy)
    company_name = models.CharField(max_length=200, blank=True)
    geo_country = models.CharField(max_length=2, blank=True)
    geo_city = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
    visit_count = models.PositiveIntegerField(default=1)
    lead_score = models.IntegerField(default=0, db_index=True)

    class Meta:
        db_table = "analytics_visitor"
        unique_together = [("website", "fingerprint_hash")]
        indexes = [
            models.Index(fields=["website", "lead_score"]),
            models.Index(fields=["website", "last_seen"]),
        ]

    def __str__(self):
        return f"Visitor({self.fingerprint_hash[:8]}@{self.website.name})"


class Session(models.Model):
    """A single browsing session for a visitor."""

    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name="sessions")
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    page_count = models.PositiveIntegerField(default=0)
    entry_page = models.URLField(max_length=1000, blank=True)
    exit_page = models.URLField(max_length=1000, blank=True)
    source = models.CharField(max_length=100, blank=True)
    medium = models.CharField(max_length=100, blank=True)
    campaign = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "analytics_session"

    def __str__(self):
        return f"Session({self.visitor_id}, {self.started_at})"


class PageEvent(TimestampMixin):
    """A single page event emitted by the tracking pixel."""

    EVENT_TYPES = [
        ("pageview", "Page View"),
        ("click", "Click"),
        ("form_submit", "Form Submit"),
        ("scroll", "Scroll"),
        ("session_end", "Session End"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name="events")
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="events"
    )
    session = models.ForeignKey(Session, null=True, on_delete=models.SET_NULL, related_name="events")
    url = models.URLField(max_length=2000)
    referrer = models.URLField(max_length=2000, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default="pageview")
    event_name = models.CharField(max_length=100, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    scroll_depth = models.IntegerField(null=True, blank=True)
    time_on_page_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "analytics_pageevent"
        indexes = [
            models.Index(fields=["website", "event_type", "timestamp"]),
            models.Index(fields=["visitor", "timestamp"]),
        ]

    def __str__(self):
        return f"PageEvent({self.event_type}: {self.url[:50]})"


class CustomFunnel(TimestampMixin):
    """User-defined conversion funnel."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="funnels"
    )
    name = models.CharField(max_length=200)
    steps = models.JSONField(default=list)
    created_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "analytics_customfunnel"

    def __str__(self):
        return f"Funnel({self.name})"


class TrackedKeyword(TimestampMixin):
    """A keyword being tracked for rank monitoring."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="tracked_keywords"
    )
    keyword = models.CharField(max_length=300, db_index=True)
    target_url = models.URLField(max_length=2000, blank=True)
    current_rank = models.IntegerField(null=True, blank=True)
    previous_rank = models.IntegerField(null=True, blank=True)
    best_rank = models.IntegerField(null=True, blank=True)
    search_volume = models.IntegerField(default=0)
    difficulty = models.IntegerField(default=0)  # 0-100

    class Meta:
        db_table = "analytics_trackedkeyword"
        unique_together = [("website", "keyword")]

    def __str__(self):
        return f"Keyword({self.keyword} #{self.current_rank})"


class KeywordRankHistory(models.Model):
    """Daily rank snapshot for a tracked keyword."""

    tracked_keyword = models.ForeignKey(
        TrackedKeyword, on_delete=models.CASCADE, related_name="history"
    )
    rank = models.IntegerField(null=True, blank=True)
    date = models.DateField(db_index=True)
    serp_features = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "analytics_keywordrankhistory"
        unique_together = [("tracked_keyword", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"Rank({self.tracked_keyword.keyword} #{self.rank} on {self.date})"
