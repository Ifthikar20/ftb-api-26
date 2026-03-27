import uuid

from django.conf import settings
from django.db import models

from core.encryption.field_encryption import EncryptedTextField
from core.mixins.timestamp_mixin import TimestampMixin


class Notification(TimestampMixin):
    """An in-app notification for a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict)
    read = models.BooleanField(default=False, db_index=True)
    action_url = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification({self.type}: {self.title})"


class NotificationPreference(models.Model):
    """User notification preferences."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    hot_lead_email = models.BooleanField(default=True)
    hot_lead_slack = models.BooleanField(default=False)
    weekly_report = models.BooleanField(default=True)
    competitor_changes = models.BooleanField(default=True)
    audit_complete = models.BooleanField(default=True)
    slack_webhook_url = EncryptedTextField(blank=True)

    class Meta:
        db_table = "notifications_notificationpreference"

    def __str__(self):
        return f"NotifPrefs({self.user.email})"


class IntegrationConnection(TimestampMixin):
    """A user's connection to an external platform for automated notifications."""

    PLATFORM_CHOICES = [
        ("slack", "Slack"),
        ("discord", "Discord"),
        ("telegram", "Telegram"),
    ]

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("realtime", "Real-time"),
    ]

    FORMAT_CHOICES = [
        ("summary", "Summary"),
        ("detailed", "Detailed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="integration_connections"
    )
    organization = models.ForeignKey(
        "accounts.Organization", null=True, blank=True,
        on_delete=models.CASCADE, related_name="integration_connections"
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    webhook_url = EncryptedTextField()
    channel_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    # Schedule
    schedule_time = models.TimeField(default="09:00")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="daily")
    message_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="summary")

    # Notification preferences — which message types to send
    notify_daily_report = models.BooleanField(default=True)
    notify_hot_leads = models.BooleanField(default=True)
    notify_trend_digest = models.BooleanField(default=True)
    notify_milestones = models.BooleanField(default=False)

    class Meta:
        db_table = "notifications_integrationconnection"
        unique_together = [("user", "platform")]

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"Integration({self.user.email}, {self.platform}, {status})"

