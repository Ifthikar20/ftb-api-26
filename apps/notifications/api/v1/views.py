from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services.notification_service import NotificationService
from apps.notifications.api.v1.serializers import NotificationSerializer, NotificationPreferenceSerializer
from core.interceptors.pagination import StandardPagination


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UnreadNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user, read=False)
        count = notifications.count()
        serializer = NotificationSerializer(notifications[:10], many=True)
        return Response({"count": count, "notifications": serializer.data})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        notification = NotificationService.mark_read(notification_id=pk, user=request.user)
        return Response(NotificationSerializer(notification).data)


class ReadAllNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = NotificationService.mark_all_read(user=request.user)
        return Response({"marked_read": count})


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        Notification.objects.filter(id=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def put(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
