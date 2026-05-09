"""Claim verification models.

A Claim is one atomic statement extracted from an LLM ranking response.
A ClaimMismatch is the verifier's verdict — populated when the claim
contradicts, outdates, or simply has no counterpart in the brand vault.
"""
from __future__ import annotations

import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class MismatchSeverity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"
    INFO = "info", "Info"


class MismatchType(models.TextChoices):
    CONTRADICTS = "contradicts", "Contradicts"
    OUTDATED = "outdated", "Outdated"
    UNKNOWN = "unknown", "Unknown"
    PARTIAL = "partial", "Partial"


class Claim(TimestampMixin):
    """One atomic claim about the brand pulled from an LLM response."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(
        "llm_ranking.LLMRankingResult",
        related_name="claims",
        on_delete=models.CASCADE,
    )
    audit = models.ForeignKey(
        "llm_ranking.LLMRankingAudit",
        related_name="claims",
        on_delete=models.CASCADE,
    )
    website = models.ForeignKey(
        "websites.Website",
        related_name="claims",
        on_delete=models.CASCADE,
    )

    text = models.TextField()
    subject = models.CharField(max_length=300, blank=True)
    predicate = models.CharField(max_length=200, blank=True)
    object = models.TextField(blank=True)

    confidence = models.FloatField(default=0.5)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "claim_verifier_claim"
        indexes = [
            models.Index(fields=["website", "audit"]),
            models.Index(fields=["audit", "result"]),
        ]

    def __str__(self):
        return f"Claim({self.subject} {self.predicate} {self.object[:30]})"


class ClaimMismatch(TimestampMixin):
    """Verifier verdict for a Claim — present iff something is off."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.OneToOneField(
        Claim, related_name="mismatch", on_delete=models.CASCADE,
    )
    matched_fact = models.ForeignKey(
        "brand_vault.BrandFact",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="mismatches",
    )

    mismatch_type = models.CharField(max_length=16, choices=MismatchType.choices)
    severity = models.CharField(
        max_length=12, choices=MismatchSeverity.choices,
        default=MismatchSeverity.MEDIUM,
    )

    factual_divergence = models.FloatField(default=0.5)
    audience_reach = models.FloatField(default=0.5)

    explanation = models.TextField(blank=True)
    dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "claim_verifier_claimmismatch"
        indexes = [
            models.Index(fields=["claim"]),
            models.Index(fields=["matched_fact"]),
            models.Index(fields=["severity", "mismatch_type"]),
        ]

    def __str__(self):
        return f"ClaimMismatch({self.mismatch_type}, {self.severity})"
