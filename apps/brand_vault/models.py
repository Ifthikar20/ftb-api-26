"""Brand Vault models — versioned atomic facts about a brand.

Phase 3 of the GEO platform. Each BrandFact is a (subject, predicate, object)
triple with a validity window and provenance pointers back to the RAG
KnowledgeChunk it was extracted from. Facts are versioned via supersede:
mutations create a new row and link the old one as superseded_by, leaving
an immutable history that the verifier and dashboard can replay.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.mixins.timestamp_mixin import TimestampMixin


class FactStatus(models.TextChoices):
    PENDING = "pending", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    AUTO = "auto", "Auto-approved"


class BrandFact(TimestampMixin):
    """A versioned atomic fact about a brand."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website",
        related_name="facts",
        on_delete=models.CASCADE,
        db_index=True,
    )

    subject = models.CharField(max_length=300, db_index=True)
    predicate = models.CharField(max_length=200, db_index=True)
    object = models.TextField()

    source_chunk = models.ForeignKey(
        "rag.KnowledgeChunk",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="facts",
    )
    source_url = models.URLField(blank=True, max_length=1000)
    extracted_by = models.CharField(max_length=24, default="llm")

    confidence = models.FloatField(default=0.5)
    status = models.CharField(
        max_length=12, choices=FactStatus.choices, default=FactStatus.PENDING,
    )

    version_from = models.DateTimeField(default=timezone.now)
    version_to = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supersedes",
    )

    product_line = models.CharField(max_length=120, blank=True)
    topic = models.CharField(max_length=120, blank=True)
    audience = models.CharField(max_length=120, blank=True)

    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "brand_vault_brandfact"
        indexes = [
            models.Index(fields=["website", "status", "version_to"]),
            models.Index(fields=["website", "subject", "predicate"]),
            models.Index(fields=["website", "product_line"]),
        ]

    def __str__(self):
        return f"BrandFact({self.subject} {self.predicate} {self.object[:40]})"


class FactRevision(TimestampMixin):
    """Immutable audit log of all changes to a BrandFact."""

    ACTION_CREATED = "created"
    ACTION_APPROVED = "approved"
    ACTION_REJECTED = "rejected"
    ACTION_SUPERSEDED = "superseded"
    ACTION_EDITED = "edited"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fact = models.ForeignKey(
        BrandFact, related_name="revisions", on_delete=models.CASCADE,
    )
    action = models.CharField(max_length=24)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "brand_vault_factrevision"
        ordering = ["-created_at"]

    def __str__(self):
        return f"FactRevision({self.fact_id}, {self.action})"


class ToneSample(TimestampMixin):
    """A short sample of brand-owned writing for voice modeling.

    Phase 4's voice guard reads these to learn the brand's tone.
    Each sample is a 80-300 word slice from a KnowledgeChunk, deduped
    via ``text_hash`` so re-running the sampler is idempotent.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website",
        related_name="tone_samples",
        on_delete=models.CASCADE,
    )
    source_chunk = models.ForeignKey(
        "rag.KnowledgeChunk",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tone_samples",
    )
    text = models.TextField()
    text_hash = models.CharField(max_length=64, db_index=True)
    word_count = models.IntegerField(default=0)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "brand_vault_tonesample"
        unique_together = [("website", "text_hash")]
        indexes = [models.Index(fields=["website"])]

    def __str__(self):
        return f"ToneSample({self.website_id}, {self.word_count}w)"


class SafetyPrompt(TimestampMixin):
    """A user-defined prompt monitored across AI models for brand-safety risks.

    Phase 5 of the GEO platform. Each prompt is re-run on a schedule by the
    safety monitor task; matches are recorded as ``SafetyAlert`` rows.
    """

    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website",
        related_name="safety_prompts",
        on_delete=models.CASCADE,
    )
    text = models.CharField(max_length=500)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="created_safety_prompts",
    )

    class Meta:
        db_table = "brand_vault_safetyprompt"
        unique_together = [("website", "text")]
        indexes = [models.Index(fields=["website", "status"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"SafetyPrompt({self.website_id}, {self.text[:40]})"


class SafetyAlert(TimestampMixin):
    """A flagged AI response that mentions the brand in a risky or inaccurate way."""

    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"
    SEVERITY_CHOICES = [
        (SEVERITY_HIGH, "High"),
        (SEVERITY_MEDIUM, "Medium"),
        (SEVERITY_LOW, "Low"),
    ]

    ISSUE_HALLUCINATION = "hallucination"
    ISSUE_UNVERIFIED = "unverified"
    ISSUE_OUTDATED = "outdated"
    ISSUE_HARMFUL = "harmful"
    ISSUE_NEGATIVE = "negative"
    ISSUE_CHOICES = [
        (ISSUE_HALLUCINATION, "Hallucination"),
        (ISSUE_UNVERIFIED, "Unverified claim"),
        (ISSUE_OUTDATED, "Outdated info"),
        (ISSUE_HARMFUL, "Harmful mention"),
        (ISSUE_NEGATIVE, "Negative mention"),
    ]

    STATUS_OPEN = "open"
    STATUS_RESOLVED = "resolved"
    STATUS_DISMISSED = "dismissed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website",
        related_name="safety_alerts",
        on_delete=models.CASCADE,
    )
    prompt = models.ForeignKey(
        SafetyPrompt,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="alerts",
    )

    model = models.CharField(max_length=40)
    prompt_text = models.CharField(max_length=500)
    snippet = models.TextField()
    issue = models.CharField(max_length=20, choices=ISSUE_CHOICES)
    detail = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN,
    )
    detected_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_safety_alerts",
    )

    class Meta:
        db_table = "brand_vault_safetyalert"
        indexes = [
            models.Index(fields=["website", "status", "-detected_at"]),
            models.Index(fields=["website", "severity"]),
        ]
        ordering = ["-detected_at"]

    def __str__(self):
        return f"SafetyAlert({self.website_id}, {self.severity}, {self.issue})"
