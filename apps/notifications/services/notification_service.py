import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notifications.models import Notification
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
            raise ResourceNotFound("Notification not found.") from None
        notification.read = True
        notification.save(update_fields=["read"])
        return notification

    @staticmethod
    def mark_all_read(*, user) -> int:
        return Notification.objects.filter(user=user, read=False).update(read=True)

    @staticmethod
    def get_unread_count(*, user) -> int:
        return Notification.objects.filter(user=user, read=False).count()

    @staticmethod
    def fire_hot_lead(*, user, lead) -> None:
        """Create hot-lead in-app notification, email alert, and Slack alert."""
        from apps.notifications.services.email_service import EmailService
        from apps.notifications.services.slack_service import SlackService

        NotificationService.create(
            user=user,
            notification_type="hot_lead",
            title=f"Hot lead detected \u2014 score {lead.score}",
            message=(
                f"A visitor on {lead.website.name} reached a lead score of {lead.score}. "
                f"Company: {lead.company or 'unknown'}."
            ),
            data={"lead_id": str(lead.id), "score": lead.score, "website_id": str(lead.website_id)},
            action_url=f"/leads/{lead.website_id}/{lead.id}/",
        )

        EmailService.send_hot_lead_alert(user=user, lead=lead)
        SlackService.send_hot_lead_alert(user=user, lead=lead)
