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
