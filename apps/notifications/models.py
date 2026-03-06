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
