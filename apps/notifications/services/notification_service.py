import logging

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.notifications.models import Notification, NotificationPreference
from core.exceptions import ResourceNotFound

logger = logging.getLogger("apps")
channel_layer = get_channel_layer()


class NotificationService:
    @staticmethod
    def create(*, user, notification_type: str, title: str, message: str, data: dict = None, action_url: str = "") -> Notification:
        """Create a notification and push it via WebSocket."""
        notification = Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            data=data or {},
            action_url=action_url,
        )

        # Push via WebSocket
        try:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{user.id}",
                {
                    "type": "notification",
                    "data": {
                        "id": str(notification.id),
                        "type": notification_type,
                        "title": title,
                        "message": message,
                    },
                },
            )
        except Exception as e:
            logger.warning(f"WebSocket notification push failed: {e}")

        return notification

    @staticmethod
    def mark_read(*, notification_id: str, user) -> Notification:
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
        except Notification.DoesNotExist:
            raise ResourceNotFound("Notification not found.")
        notification.read = True
        notification.save(update_fields=["read"])
        return notification

    @staticmethod
    def mark_all_read(*, user) -> int:
        return Notification.objects.filter(user=user, read=False).update(read=True)

    @staticmethod
    def get_unread_count(*, user) -> int:
        return Notification.objects.filter(user=user, read=False).count()
