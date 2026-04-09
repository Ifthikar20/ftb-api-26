from rest_framework import status
from rest_framework.response import Response

from apps.notifications.api.v1.serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from apps.notifications.models import Notification, NotificationPreference
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
