import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class AgentRun(TimestampMixin):
    """A single execution of an AI agent — tracks the full observe→think→act loop."""

    AGENT_TYPES = [
        ("opportunity_finder", "Opportunity Finder"),
        ("campaign_runner", "Campaign Runner"),
        ("competitor_watcher", "Competitor Watcher"),
        ("anomaly_responder", "Anomaly Responder"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused — Awaiting Approval"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    TRIGGER_CHOICES = [
        ("scheduled", "Scheduled"),
        ("manual", "Manual"),
        ("event", "Event-Triggered"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="agent_runs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_runs",
    )
    agent_type = models.CharField(max_length=50, choices=AGENT_TYPES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="manual")

    # Agent context — accumulated knowledge across steps
    context = models.JSONField(default=dict, blank=True)

    # Results
    summary = models.TextField(blank=True, help_text="AI-generated summary of what the agent did")
    findings = models.JSONField(default=list, blank=True, help_text="Structured findings/recommendations")

    # Approval workflow
    requires_approval = models.BooleanField(default=True)
    approval_request = models.TextField(blank=True, help_text="What the agent is asking approval for")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_agent_runs",
    )

    # Metrics
    steps_count = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    duration_ms = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "agents_agentrun"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "-created_at"]),
            models.Index(fields=["agent_type", "status"]),
        ]

    def __str__(self):
        return f"AgentRun({self.get_agent_type_display()}, {self.status})"


class AgentStep(TimestampMixin):
    """A single step within an agent run — one tool call with its reasoning and result."""

    STATUS_CHOICES = [
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_run = models.ForeignKey(
        AgentRun, on_delete=models.CASCADE, related_name="steps"
    )
    step_number = models.IntegerField()

    # What Claude decided
    reasoning = models.TextField(help_text="Why the agent chose this action")
    tool_name = models.CharField(max_length=100)
    tool_params = models.JSONField(default=dict)

    # What happened
    tool_result = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    error_message = models.TextField(blank=True)

    # Metrics
    tokens_used = models.IntegerField(default=0)
    duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "agents_agentstep"
        ordering = ["step_number"]
        unique_together = [("agent_run", "step_number")]

    def __str__(self):
        return f"Step {self.step_number}: {self.tool_name}"
