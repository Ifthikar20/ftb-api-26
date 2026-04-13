from rest_framework import status
from rest_framework.response import Response

from apps.notifications.api.v1.serializers import (
    IntegrationConnectionSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from apps.notifications.models import IntegrationConnection, Notification, NotificationPreference
from apps.notifications.services.notification_service import NotificationService
from core.views import TenantScopedAPIView, TenantScopedListAPIView


class NotificationListView(TenantScopedListAPIView):
    """User-scoped (not website-scoped). Uses the base for auth + pagination."""

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        return self.paginated_response(notifications, NotificationSerializer)


class UnreadNotificationsView(TenantScopedAPIView):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user, read=False)
        count = notifications.count()
        serializer = NotificationSerializer(notifications[:10], many=True)
        return Response({"count": count, "notifications": serializer.data})


class NotificationReadView(TenantScopedAPIView):
    def put(self, request, pk):
        notification = NotificationService.mark_read(notification_id=pk, user=request.user)
        return Response(NotificationSerializer(notification).data)


class ReadAllNotificationsView(TenantScopedAPIView):
    def post(self, request):
        count = NotificationService.mark_all_read(user=request.user)
        return Response({"marked_read": count})


class NotificationDetailView(TenantScopedAPIView):
    def delete(self, request, pk):
        Notification.objects.filter(id=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationPreferencesView(TenantScopedAPIView):
    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def put(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ── Integration Connections (Slack / Discord / Telegram) ──────────────────────


class IntegrationConnectionListView(TenantScopedAPIView):
    """
    GET  — list all connected integrations for the current user.
    POST — create or update a connection (upsert by platform).
    """

    def get(self, request):
        connections = IntegrationConnection.objects.filter(user=request.user)
        serializer = IntegrationConnectionSerializer(connections, many=True)
        return Response({"data": serializer.data})

    def post(self, request):
        platform = request.data.get("platform", "")
        if platform not in dict(IntegrationConnection.PLATFORM_CHOICES):
            return Response(
                {"error": f"Invalid platform: {platform}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Upsert: one connection per user per platform
        connection, created = IntegrationConnection.objects.get_or_create(
            user=request.user,
            platform=platform,
            defaults={"webhook_url": ""},
        )

        serializer = IntegrationConnectionSerializer(
            connection, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Send a test message on first connect
        if created or not connection.is_active:
            connection.is_active = True
            connection.save(update_fields=["is_active"])
            self._send_test_message(connection)

        return Response(
            {"data": IntegrationConnectionSerializer(connection).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @staticmethod
    def _send_test_message(connection):
        """Send a test/welcome message to verify the webhook works."""
        import logging
        logger = logging.getLogger("apps")
        try:
            if connection.platform == "slack":
                from apps.notifications.services.slack_service import SlackService
                SlackService.send_message(
                    webhook_url=connection.webhook_url,
                    text="✅ FetchBot connected! You'll receive growth reports here.",
                )
            elif connection.platform == "discord":
                from apps.notifications.services.discord_service import DiscordService
                DiscordService.send_message(
                    webhook_url=connection.webhook_url,
                    title="✅ FetchBot Connected",
                    description="You'll receive daily growth reports, hot lead alerts, and trend intelligence here.",
                )
            elif connection.platform == "telegram":
                from apps.notifications.services.telegram_service import TelegramService
                TelegramService.send_message(
                    chat_id=connection.webhook_url,
                    text="✅ *FetchBot connected!*\nYou'll receive growth reports here.",
                )
        except Exception as e:
            logger.warning(f"Test message failed for {connection.platform}: {e}")


class IntegrationConnectionDetailView(TenantScopedAPIView):
    """
    PUT    — update an integration connection.
    DELETE — disconnect (delete) an integration.
    """

    def put(self, request, pk):
        try:
            connection = IntegrationConnection.objects.get(id=pk, user=request.user)
        except IntegrationConnection.DoesNotExist:
            return Response({"error": "Connection not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = IntegrationConnectionSerializer(connection, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})

    def delete(self, request, pk):
        IntegrationConnection.objects.filter(id=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

