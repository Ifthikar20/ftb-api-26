import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class SocialLeadSource(TimestampMixin):
    """
    Configuration for a social media lead source connected to a website.
    Stores credentials and webhook settings for each platform integration.
    """

    PLATFORM_FACEBOOK = "facebook"
    PLATFORM_INSTAGRAM = "instagram"
    PLATFORM_LINKEDIN = "linkedin"
    PLATFORM_TIKTOK = "tiktok"
    PLATFORM_X = "x"
    PLATFORM_GOOGLE = "google"
    PLATFORM_CHOICES = [
        (PLATFORM_FACEBOOK, "Facebook Lead Ads"),
        (PLATFORM_INSTAGRAM, "Instagram (via Facebook)"),
        (PLATFORM_LINKEDIN, "LinkedIn Lead Gen Forms"),
        (PLATFORM_TIKTOK, "TikTok Lead Generation"),
        (PLATFORM_X, "X (Twitter)"),
        (PLATFORM_GOOGLE, "Google Lead Form Extensions"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="social_lead_sources"
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    label = models.CharField(
        max_length=200, blank=True, help_text="e.g. 'Facebook - Summer Campaign'"
    )
    is_active = models.BooleanField(default=True)

    # Platform-specific identifiers
    account_id = models.CharField(
        max_length=200, blank=True, help_text="Ad account ID or page ID"
    )
    form_id = models.CharField(
        max_length=200, blank=True, help_text="Lead form / lead gen form ID"
    )
    campaign_name = models.CharField(max_length=300, blank=True)

    # OAuth / API credentials (encrypted at rest via field_encryption if needed)
    access_token = models.TextField(blank=True, help_text="OAuth access token")
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    webhook_verify_token = models.CharField(
        max_length=200,
        blank=True,
        help_text="Random token used to verify webhook ownership (Facebook hub.verify_token)",
    )

    # Stats
    total_leads_imported = models.IntegerField(default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "social_leads_source"
        ordering = ["-created_at"]
        unique_together = [("website", "platform", "form_id")]

    def __str__(self):
        return f"{self.get_platform_display()} — {self.label or self.form_id}"


class SocialLead(TimestampMixin):
    """
    A lead captured from a social media platform lead form.
    Automatically created when a webhook fires or during polling.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        SocialLeadSource, on_delete=models.CASCADE, related_name="leads"
    )
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="social_leads"
    )

    # Platform-side identifiers
    external_lead_id = models.CharField(
        max_length=300, blank=True, db_index=True,
        help_text="Platform-assigned lead ID (prevents duplicate imports)",
    )

    # Contact info
    first_name = models.CharField(max_length=200, blank=True)
    last_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    linkedin_profile = models.URLField(blank=True)

    # Form responses (platform-specific fields stored as JSON)
    form_data = models.JSONField(
        default=dict, help_text="Raw field responses from the lead form."
    )

    # Linked FetchBot lead (created automatically)
    lead = models.OneToOneField(
        "leads.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="social_lead",
    )

    # Processing flags
    is_processed = models.BooleanField(
        default=False, help_text="Whether a Lead record has been created."
    )

    class Meta:
        db_table = "social_leads_lead"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["website", "is_processed"]),
            models.Index(fields=["source", "external_lead_id"]),
        ]

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip() or self.email or "Unknown"
        return f"SocialLead({self.source.get_platform_display()}, {name})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
