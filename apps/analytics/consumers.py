import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class LiveAnalyticsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time visitor stream.
    Authenticates via JWT token in query string.
    Broadcasts new visitor events to connected clients.
    """

    async def connect(self):
        self.website_id = self.scope["url_route"]["kwargs"]["website_id"]
        self.group_name = f"analytics_{self.website_id}"

        user = self.scope.get("user")
        if not user or not await self.has_access(user, self.website_id):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def visitor_event(self, event):
        """Send visitor event to WebSocket client."""
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def has_access(self, user, website_id):
        from apps.websites.models import Website
        return Website.objects.filter(id=website_id, user=user).exists()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time user notifications."""

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4003)
            return

        self.group_name = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))
