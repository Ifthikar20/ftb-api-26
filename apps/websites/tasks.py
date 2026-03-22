import json
import logging

import requests
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps")

MAX_RETRIES = 3
RETRY_BACKOFF = 60  # seconds


@shared_task(
    name="apps.websites.tasks.deliver_webhook",
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
)
def deliver_webhook(self, *, endpoint_id: int, event: str, payload: dict) -> None:
    """Deliver a single webhook event to one endpoint, with retry on failure."""
    from apps.websites.models import WebhookEndpoint
    from apps.websites.services.webhook_service import WebhookService

    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        return

    full_payload = WebhookService.build_payload(event=event, data=payload)
    body = json.dumps(full_payload)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FetchBot-Webhook/1.0",
        "X-FetchBot-Event": event,
    }
    if endpoint.secret:
        headers["X-FetchBot-Signature"] = WebhookService.sign_payload(
            secret=endpoint.secret, body=body
        )

    try:
        response = requests.post(endpoint.url, data=body, headers=headers, timeout=10)
        response.raise_for_status()
        WebhookEndpoint.objects.filter(pk=endpoint_id).update(
            last_triggered_at=timezone.now(),
            failure_count=0,
        )
        logger.info("Webhook delivered to %s for event %s", endpoint.url, event)
    except Exception as exc:
        WebhookEndpoint.objects.filter(pk=endpoint_id).update(
            failure_count=endpoint.failure_count + 1,
        )
        logger.warning(
            "Webhook delivery failed to %s (attempt %d/%d): %s",
            endpoint.url,
            self.request.retries + 1,
            MAX_RETRIES,
            exc,
        )
        raise self.retry(exc=exc, countdown=RETRY_BACKOFF * (2 ** self.request.retries)) from None
