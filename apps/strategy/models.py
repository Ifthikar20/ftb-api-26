import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin
from core.utils.constants import ActionStatus, ContentType


class Strategy(TimestampMixin):
    """An AI-generated growth strategy."""

    PLAN_TYPES = [("30", "30 Days"), ("60", "60 Days"), ("90", "90 Days")]
    STATUS_CHOICES = [("active", "Active"), ("completed", "Completed"), ("archived", "Archived")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="strategies"
    )
    plan_type = models.CharField(max_length=5, choices=PLAN_TYPES, default="30")
    generated_at = models.DateTimeField(auto_now_add=True)
    raw_response = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    completion_pct = models.IntegerField(default=0)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = "strategy_strategy"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Strategy({self.website.name}, {self.plan_type}d)"


class Action(TimestampMixin):
    """A specific action item within a strategy."""

    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name="actions")
    title = models.CharField(max_length=300)
    description = models.TextField()
    action_type = models.CharField(max_length=50, blank=True)
    estimated_impact = models.CharField(max_length=20, blank=True)
    estimated_time_minutes = models.IntegerField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ActionStatus.choices, default=ActionStatus.TODO)
    completed_at = models.DateTimeField(null=True, blank=True)
    ai_reasoning = models.TextField(blank=True)
    week_number = models.IntegerField(default=1)

    class Meta:
        db_table = "strategy_action"
        ordering = ["week_number", "id"]

    def __str__(self):
        return f"Action({self.title[:50]})"


class ContentCalendarEntry(TimestampMixin):
    """A content calendar entry."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="calendar_entries"
    )
    title = models.CharField(max_length=300)
    topic = models.CharField(max_length=300, blank=True)
    content_type = models.CharField(max_length=20, choices=ContentType.choices, default=ContentType.BLOG)
    scheduled_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, default="scheduled")
    ai_generated = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "strategy_contentcalendarentry"
        ordering = ["scheduled_date"]

    def __str__(self):
        return f"CalEntry({self.title[:50]}, {self.scheduled_date})"


class NicheAnalysis(TimestampMixin):
    """Niche positioning analysis for a website."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="niche_analyses"
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    clusters = models.JSONField(default=list)
    opportunities = models.JSONField(default=list)
    positioning = models.JSONField(default=dict)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = "strategy_nicheanalysis"
        ordering = ["-generated_at"]


class ChatMessage(TimestampMixin):
    """A message in the AI strategy chat."""

    ROLES = [("user", "User"), ("assistant", "Assistant")]

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="chat_messages"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages"
    )
    role = models.CharField(max_length=20, choices=ROLES)
    content = models.TextField()
    tokens_used = models.IntegerField(default=0)

    class Meta:
        db_table = "strategy_chatmessage"
        ordering = ["created_at"]

    def __str__(self):
        return f"ChatMessage({self.role}, {self.content[:30]})"


class MorningBrief(models.Model):
    """Daily AI-generated morning brief."""

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="morning_briefs"
    )
    date = models.DateField(db_index=True)
    content = models.TextField()
    metrics_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "strategy_morningbrief"
        unique_together = [("website", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"Brief({self.website.name}, {self.date})"
