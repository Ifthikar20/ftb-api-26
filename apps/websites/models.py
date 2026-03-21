import uuid

from django.conf import settings
from django.db import models

from core.encryption.field_encryption import EncryptedTextField
from core.mixins.timestamp_mixin import TimestampMixin
from core.mixins.soft_delete_mixin import SoftDeleteMixin
from core.utils.constants import UserRole


class Website(SoftDeleteMixin, TimestampMixin):
    """A website tracked by FetchBot."""

    PLATFORM_TYPES = [
        ("shopify", "Shopify"),
        ("wordpress", "WordPress"),
        ("woocommerce", "WooCommerce"),
        ("custom", "Custom / Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="websites"
    )
    url = models.URLField(max_length=500)
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, blank=True)
    pixel_key = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    pixel_verified = models.BooleanField(default=False)
    pixel_verified_at = models.DateTimeField(null=True, blank=True)
    platform_type = models.CharField(max_length=20, choices=PLATFORM_TYPES, default="custom", blank=True)
    onboarding_completed = models.BooleanField(default=False)
    crawl_status = models.CharField(max_length=20, default="pending")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "websites_website"
        unique_together = [("user", "url")]

    def __str__(self):
        return f"{self.name} ({self.url})"


class WebsiteSettings(TimestampMixin):
    website = models.OneToOneField(Website, on_delete=models.CASCADE, related_name="settings")
    track_anonymous = models.BooleanField(default=True)
    notify_hot_leads = models.BooleanField(default=True)
    hot_lead_threshold = models.IntegerField(default=70)
    weekly_report = models.BooleanField(default=True)

    class Meta:
        db_table = "websites_websitesettings"


class WebsiteMembership(TimestampMixin):
    """Team members with role-based access to a website."""

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="website_memberships"
    )
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.VIEWER)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    accepted = models.BooleanField(default=False)

    class Meta:
        db_table = "websites_websitemembership"
        unique_together = [("website", "user")]

    def __str__(self):
        return f"{self.user.email} — {self.role} on {self.website.name}"


class Integration(TimestampMixin):
    """External service integrations — types driven by core.integrations registry."""

    INTEGRATION_TYPES = [
        ("ga", "Google Analytics"),
        ("gsc", "Google Search Console"),
        ("facebook", "Facebook Ads"),
        ("shopify", "Shopify"),
    ]

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="integrations")
    type = models.CharField(max_length=20, choices=INTEGRATION_TYPES)
    access_token = EncryptedTextField(blank=True)
    refresh_token = EncryptedTextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # e.g. customer_id, channel_id
    connected_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "websites_integration"
        unique_together = [("website", "type")]

    def __str__(self):
        return f"{self.get_type_display()} — {self.website.name}"

    @property
    def config(self):
        """Get this integration's config from the registry."""
        from core.integrations import get_registry
        return get_registry().get(self.type)

    def is_token_expired(self) -> bool:
        if not self.token_expires_at:
            return False
        from django.utils import timezone
        return timezone.now() >= self.token_expires_at

    def needs_token_refresh(self, buffer_seconds: int = 900) -> bool:
        """Check if token needs refresh (default: 15 min before expiry)."""
        if not self.token_expires_at:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() >= (self.token_expires_at - timedelta(seconds=buffer_seconds))
