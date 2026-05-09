"""Content Studio models — Phase 4 backend.

Models drive the content authoring loop:

* :class:`ContentBrief` — a ranked content gap pulled from the recommendation
  engine (visibility, accuracy, citation).
* :class:`ContentDraft` — the LLM-drafted artefact for a brief, with voice
  and accuracy quality scores attached.
* :class:`PublishTarget` — a configured publishing destination per tenant.
* :class:`PublishLog` — append-only audit of publish attempts (dry-run or real).
* :class:`ROIAttribution` — measured score lift after a draft is published.
"""
from __future__ import annotations

import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class GapType(models.TextChoices):
    VISIBILITY = "visibility", "Visibility"
    ACCURACY = "accuracy", "Accuracy"
    CITATION = "citation", "Citation"


class ContentFormat(models.TextChoices):
    BLOG = "blog", "Blog"
    FAQ = "faq", "FAQ"
    REDDIT_ANSWER = "reddit_answer", "Reddit answer"
    JSON_LD = "json_ld", "JSON-LD"
    LANDING_PAGE = "landing_page", "Landing page"
    META_DESCRIPTION = "meta_description", "Meta description"


class BriefStatus(models.TextChoices):
    OPEN = "open", "Open"
    DRAFTED = "drafted", "Drafted"
    SKIPPED = "skipped", "Skipped"
    EXPIRED = "expired", "Expired"


class DraftStatus(models.TextChoices):
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    EDITED = "edited", "Edited"
    APPROVED = "approved", "Approved"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class PublishStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    PUBLISHED = "published", "Published"
    FAILED = "failed", "Failed"


class ContentBrief(TimestampMixin):
    """A specific content gap to address, ranked by impact."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", related_name="briefs", on_delete=models.CASCADE,
    )
    gap_type = models.CharField(max_length=16, choices=GapType.choices)
    impact_score = models.FloatField(default=0.0, db_index=True)

    target_format = models.CharField(max_length=20, choices=ContentFormat.choices)
    target_prompt = models.ForeignKey(
        "prompt_library.Prompt", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="briefs",
    )
    target_claim_mismatch = models.ForeignKey(
        "claim_verifier.ClaimMismatch", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="briefs",
    )
    target_source_class = models.CharField(max_length=24, blank=True)

    headline = models.CharField(max_length=300)
    description = models.TextField()
    suggested_structure = models.JSONField(default=dict)
    target_keywords = models.JSONField(default=list)
    grounded_facts = models.ManyToManyField(
        "brand_vault.BrandFact", related_name="briefs", blank=True,
    )

    # Idempotency key for duplicate suppression — derived from
    # (gap_type, target_*). Indexed but not unique because we want
    # to allow re-creation after a brief was skipped/expired.
    dedupe_key = models.CharField(max_length=128, blank=True, db_index=True)

    status = models.CharField(
        max_length=12, choices=BriefStatus.choices,
        default=BriefStatus.OPEN, db_index=True,
    )

    class Meta:
        db_table = "content_studio_contentbrief"
        ordering = ["-impact_score", "-created_at"]
        indexes = [
            models.Index(fields=["website", "status", "-impact_score"]),
            models.Index(fields=["website", "gap_type"]),
        ]

    def __str__(self):
        return f"ContentBrief({self.gap_type}, {self.headline[:40]})"


class ContentDraft(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brief = models.ForeignKey(
        ContentBrief, related_name="drafts", on_delete=models.CASCADE,
    )
    website = models.ForeignKey(
        "websites.Website", related_name="drafts", on_delete=models.CASCADE,
    )

    title = models.CharField(max_length=400)
    body_markdown = models.TextField()
    body_html = models.TextField(blank=True)
    json_ld = models.JSONField(null=True, blank=True)

    word_count = models.IntegerField(default=0)

    voice_score = models.FloatField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    voice_notes = models.TextField(blank=True)
    accuracy_notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=12, choices=DraftStatus.choices,
        default=DraftStatus.GENERATING, db_index=True,
    )
    generated_by = models.CharField(max_length=24, default="anthropic")
    revision = models.IntegerField(default=1)

    class Meta:
        db_table = "content_studio_contentdraft"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "status"]),
            models.Index(fields=["brief"]),
        ]

    def __str__(self):
        return f"ContentDraft({self.title[:40]}, rev{self.revision})"


class PublishTarget(TimestampMixin):
    """A configured publish destination per tenant."""

    PROVIDER_CHOICES = [
        ("wordpress", "WordPress"),
        ("webflow", "Webflow"),
        ("shopify", "Shopify"),
        ("hubspot", "HubSpot"),
        ("manual", "Manual export"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", related_name="publish_targets",
        on_delete=models.CASCADE,
    )
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES)
    label = models.CharField(max_length=120, blank=True)
    config = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "content_studio_publishtarget"
        unique_together = [("website", "provider", "label")]

    def __str__(self):
        return f"PublishTarget({self.provider}, {self.label or 'default'})"


class PublishLog(TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(
        ContentDraft, related_name="publish_logs", on_delete=models.CASCADE,
    )
    target = models.ForeignKey(PublishTarget, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=12, choices=PublishStatus.choices,
        default=PublishStatus.PENDING,
    )
    external_id = models.CharField(max_length=200, blank=True)
    external_url = models.URLField(blank=True, max_length=1000)
    error_message = models.TextField(blank=True)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)

    class Meta:
        db_table = "content_studio_publishlog"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PublishLog({self.status}, draft={self.draft_id})"


class ROIAttribution(TimestampMixin):
    """Tracks score lift attributed to a published draft."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft = models.ForeignKey(
        ContentDraft, related_name="roi_records", on_delete=models.CASCADE,
    )
    website = models.ForeignKey(
        "websites.Website", related_name="roi_records", on_delete=models.CASCADE,
    )

    measured_at = models.DateTimeField()
    days_since_publish = models.IntegerField()

    visibility_before = models.FloatField(null=True, blank=True)
    visibility_after = models.FloatField(null=True, blank=True)
    visibility_lift = models.FloatField(null=True, blank=True)

    citation_count_before = models.IntegerField(default=0)
    citation_count_after = models.IntegerField(default=0)

    accuracy_lift = models.FloatField(null=True, blank=True)

    affected_prompts = models.JSONField(default=list)

    class Meta:
        db_table = "content_studio_roiattribution"
        ordering = ["-measured_at"]

    def __str__(self):
        return f"ROIAttribution(draft={self.draft_id}, lift={self.visibility_lift})"
