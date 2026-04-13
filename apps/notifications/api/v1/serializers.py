from rest_framework import serializers

from apps.notifications.models import IntegrationConnection, Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "message", "data", "read", "action_url", "created_at"]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "hot_lead_email", "hot_lead_slack", "weekly_report",
            "competitor_changes", "audit_complete", "slack_webhook_url",
        ]


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationConnection
        fields = [
            "id", "platform", "webhook_url", "channel_name", "is_active",
            "schedule_time", "frequency", "message_format",
            "notify_daily_report", "notify_hot_leads",
            "notify_trend_digest", "notify_milestones",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

