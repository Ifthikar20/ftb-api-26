import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("apps")
channel_layer = get_channel_layer()


class RealtimeService:
    @staticmethod
    def broadcast_visitor_event(website_id: str, event_data: dict):
        """Push a visitor event to all connected WebSocket clients for this website."""
        try:
            async_to_sync(channel_layer.group_send)(
                f"analytics_{website_id}",
                {"type": "visitor_event", "data": event_data},
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast visitor event: {e}")
