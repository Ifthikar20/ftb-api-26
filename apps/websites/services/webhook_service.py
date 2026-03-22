"""
Outbound webhook dispatch service.

Events are delivered asynchronously via Celery. Each endpoint receives an
HMAC-SHA256 signed POST with a JSON payload.
"""
import hashlib
import hmac
import logging
import uuid

from django.utils import timezone

logger = logging.getLogger("apps")


class WebhookService:
    @staticmethod
    def dispatch(*, website, event: str, payload: dict) -> None:
        """Queue webhook delivery for all active endpoints subscribed to this event."""
        from apps.websites.models import WebhookEndpoint

        endpoints = WebhookEndpoint.objects.filter(
            website=website,
            is_active=True,
        )

        for endpoint in endpoints:
            if not endpoint.subscribes_to(event):
                continue
            try:
                from apps.websites.tasks import deliver_webhook
                deliver_webhook.delay(
                    endpoint_id=endpoint.id,
                    event=event,
                    payload=payload,
                )
            except Exception as e:
                logger.error(
                    "Failed to queue webhook delivery to %s for event %s: %s",
                    endpoint.url,
                    event,
                    e,
                )

    @staticmethod
    def build_payload(*, event: str, data: dict) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "event": event,
            "timestamp": timezone.now().isoformat(),
            "data": data,
        }

    @staticmethod
    def sign_payload(*, secret: str, body: str) -> str:
        """Return HMAC-SHA256 hex signature for the payload."""
        mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256)
        return mac.hexdigest()
