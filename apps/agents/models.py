"""Models for the hireable-agents feature.

An agent "type" is defined in code (``apps/agents/catalog.py``); these models
store the per-user, per-website state of a *hired* agent: its schedule, the
insights it produces, the actions it proposes (gated by human approval), and
its chat transcript.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.mixins.timestamp_mixin import TimestampMixin


class HiredAgent(TimestampMixin):
    """One agent hired by a user for a specific website.

    Mirrors the scheduling/resilience shape of
    ``apps.llm_ranking.models.LLMRankingSchedule`` so the dispatcher logic is
    consistent across the codebase.
    """

    FREQUENCY_DAILY = "daily"
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, "Daily"),
        (FREQUENCY_WEEKLY, "Weekly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hired_agents"
    )
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="hired_agents"
    )
    # References a key in ``apps.agents.catalog.CATALOG``.
    agent_key = models.CharField(max_length=64, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # Delivery target for the daily digest (Slack/Discord connection).
    slack_connection = models.ForeignKey(
        "notifications.IntegrationConnection",
        null=True, blank=True,
        on_delete=models.SET_NULL, related_name="hired_agents",
    )
    config = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )

    # Scheduling + resilience (mirror LLMRankingSchedule).
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default=FREQUENCY_DAILY
    )
    schedule_time = models.TimeField(default="09:00")
    next_run_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    auto_pause_threshold = models.IntegerField(default=3)

    class Meta:
        db_table = "agents_hiredagent"
        ordering = ["-created_at"]
        unique_together = [("website", "agent_key")]
        indexes = [
            models.Index(fields=["is_active", "next_run_at"]),
            models.Index(fields=["user", "website"]),
        ]

    def __str__(self):
        status = "active" if self.is_active else "paused"
        return f"HiredAgent({self.agent_key}, {self.website_id}, {status})"


class AgentInsight(TimestampMixin):
    """One daily insight produced by a hired agent's run."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hired_agent = models.ForeignKey(
        HiredAgent, on_delete=models.CASCADE, related_name="insights"
    )
    run_date = models.DateField(db_index=True)
    title = models.CharField(max_length=300)
    summary_markdown = models.TextField()
    # Structured metrics the agent computed/used, JSON-serialisable.
    data = models.JSONField(default=dict, blank=True)
    # References to source records (audit ids, brief ids, etc.).
    source_refs = models.JSONField(default=list, blank=True)
    # Which channels this insight was delivered to (["slack", "in_app"]).
    delivered_channels = models.JSONField(default=list, blank=True)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        db_table = "agents_insight"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hired_agent", "-created_at"])]

    def __str__(self):
        return f"AgentInsight({self.title[:40]})"


class AgentAction(TimestampMixin):
    """An action an agent proposes; executed only after human approval."""

    STATUS_PROPOSED = "proposed"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_EXECUTING = "executing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PROPOSED, "Proposed"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXECUTING, "Executing"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hired_agent = models.ForeignKey(
        HiredAgent, on_delete=models.CASCADE, related_name="actions"
    )
    insight = models.ForeignKey(
        AgentInsight, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="actions",
    )
    action_type = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=300)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_PROPOSED, db_index=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    executed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "agents_action"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hired_agent", "status"])]

    def __str__(self):
        return f"AgentAction({self.action_type}, {self.status})"


class AgentMessage(TimestampMixin):
    """A single chat message between a user and a hired agent."""

    ROLE_USER = "user"
    ROLE_AGENT = "agent"
    ROLE_CHOICES = [(ROLE_USER, "User"), (ROLE_AGENT, "Agent")]

    CHANNEL_IN_APP = "in_app"
    CHANNEL_SLACK = "slack"
    CHANNEL_DISCORD = "discord"
    CHANNEL_CHOICES = [
        (CHANNEL_IN_APP, "In-app"),
        (CHANNEL_SLACK, "Slack"),
        (CHANNEL_DISCORD, "Discord"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hired_agent = models.ForeignKey(
        HiredAgent, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    text = models.TextField()
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default=CHANNEL_IN_APP)
    # Slack threading identifiers (Phase B).
    slack_ts = models.CharField(max_length=40, blank=True)
    thread_ts = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = "agents_message"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["hired_agent", "created_at"])]

    def __str__(self):
        return f"AgentMessage({self.role}, {self.text[:30]})"
