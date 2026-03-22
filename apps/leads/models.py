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


class EmailCampaign(TimestampMixin):
    """An outbound email campaign sent to a set of leads."""

    STATUS_DRAFT = "draft"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="email_campaigns"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_campaigns"
    )
    subject = models.CharField(max_length=500)
    body = models.TextField()  # HTML content
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    segment = models.ForeignKey(
        "LeadSegment", null=True, blank=True, on_delete=models.SET_NULL, related_name="campaigns"
    )
    canva_design_url = models.URLField(blank=True)  # Optional Canva design reference
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    # Mailchimp campaign ID if synced
    mailchimp_campaign_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "leads_emailcampaign"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Campaign({self.subject[:50]}, {self.status})"

    @property
    def open_rate(self) -> float:
        if not self.recipient_count:
            return 0.0
        return round(self.open_count / self.recipient_count * 100, 1)

    @property
    def click_rate(self) -> float:
        if not self.recipient_count:
            return 0.0
        return round(self.click_count / self.recipient_count * 100, 1)


class CampaignRecipient(TimestampMixin):
    """A single lead recipient within an email campaign."""

    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_OPENED = "opened"
    STATUS_CLICKED = "clicked"
    STATUS_BOUNCED = "bounced"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_SENT, "Sent"),
        (STATUS_OPENED, "Opened"),
        (STATUS_CLICKED, "Clicked"),
        (STATUS_BOUNCED, "Bounced"),
        (STATUS_FAILED, "Failed"),
    ]

    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name="recipients")
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="campaign_receipts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    tracking_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leads_campaignrecipient"
        unique_together = [("campaign", "lead")]

    def __str__(self):
        return f"Recipient({self.lead_id} in {self.campaign_id})"


class LeadEmail(TimestampMixin):
    """Emails sent to leads from the FetchBot platform."""

    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("bounced", "Bounced"),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="emails")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_lead_emails"
    )
    subject = models.CharField(max_length=500)
    body = models.TextField()
    to_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leads_leademail"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Email to {self.to_email} — {self.subject[:40]}"
