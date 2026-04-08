import ipaddress
import json
import logging
import socket
from urllib.parse import urlparse

import requests
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps")

MAX_RETRIES = 3
RETRY_BACKOFF = 60  # seconds
DISABLE_AFTER_FAILURES = 10  # auto-disable endpoint after N consecutive failures
MAX_PAYLOAD_BYTES = 256 * 1024  # 256 KB cap per spec


def _is_safe_webhook_url(url: str) -> tuple[bool, str]:
    """SSRF guard for outbound webhooks.

    Returns (ok, reason). Rejects:
      - non-HTTPS URLs
      - hosts that resolve to private, loopback, link-local, multicast,
        reserved, or unspecified IP ranges (incl. cloud metadata 169.254.169.254)
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "unparseable url"

    if parsed.scheme != "https":
        return False, "https required"
    if not parsed.hostname:
        return False, "missing hostname"

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        return False, f"dns failure: {exc}"

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"invalid ip {ip_str}"
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, f"blocked ip range {ip_str}"
    return True, ""


@shared_task(
    name="apps.websites.tasks.deliver_webhook",
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_BACKOFF,
    queue="webhooks",
)
def deliver_webhook(self, *, endpoint_id: int, event: str, payload: dict) -> None:
    """Deliver a single webhook event to one endpoint, with retry on failure."""
    from apps.websites.models import WebhookEndpoint
    from apps.websites.services.webhook_service import WebhookService

    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        return

    ok, reason = _is_safe_webhook_url(endpoint.url)
    if not ok:
        logger.warning(
            "Webhook delivery blocked by SSRF guard: endpoint=%s url=%s reason=%s",
            endpoint_id,
            endpoint.url,
            reason,
        )
        WebhookEndpoint.objects.filter(pk=endpoint_id).update(is_active=False)
        return

    full_payload = WebhookService.build_payload(event=event, data=payload)
    body = json.dumps(full_payload)
    if len(body.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        logger.warning(
            "Webhook payload exceeds %d bytes for endpoint %s event %s; dropping",
            MAX_PAYLOAD_BYTES,
            endpoint_id,
            event,
        )
        return

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
        response = requests.post(
            endpoint.url, data=body, headers=headers, timeout=10, allow_redirects=False
        )
        response.raise_for_status()
        WebhookEndpoint.objects.filter(pk=endpoint_id).update(
            last_triggered_at=timezone.now(),
            failure_count=0,
        )
        logger.info("Webhook delivered to %s for event %s", endpoint.url, event)
    except Exception as exc:
        new_failure_count = endpoint.failure_count + 1
        update_fields = {"failure_count": new_failure_count}
        if new_failure_count >= DISABLE_AFTER_FAILURES:
            update_fields["is_active"] = False
            logger.error(
                "Webhook endpoint %s auto-disabled after %d consecutive failures",
                endpoint_id,
                new_failure_count,
            )
        WebhookEndpoint.objects.filter(pk=endpoint_id).update(**update_fields)
        logger.warning(
            "Webhook delivery failed to %s (attempt %d/%d): %s",
            endpoint.url,
            self.request.retries + 1,
            MAX_RETRIES,
            exc,
        )
        if new_failure_count >= DISABLE_AFTER_FAILURES:
            return
        raise self.retry(exc=exc, countdown=RETRY_BACKOFF * (2 ** self.request.retries)) from None


@shared_task(
    name="apps.websites.tasks.refresh_expiring_tokens",
    queue="integrations",
)
def refresh_expiring_tokens() -> dict:
    """Refresh OAuth tokens for any Integration whose access_token expires soon.

    Runs every 15 minutes via Celery beat. Each integration type that uses OAuth
    must register a refresh callable in `core.integrations.registry`. Integrations
    without a registered refresh callable are skipped.
    """
    from apps.websites.models import Integration

    refreshed = 0
    skipped = 0
    failed = 0

    candidates = Integration.objects.filter(
        is_active=True,
        token_expires_at__isnull=False,
    )
    for integration in candidates:
        if not integration.needs_token_refresh():
            continue

        try:
            config = integration.config
        except Exception as exc:
            logger.warning(
                "refresh_expiring_tokens: no registry config for type=%s id=%s: %s",
                integration.type,
                integration.id,
                exc,
            )
            skipped += 1
            continue

        refresh_fn = getattr(config, "refresh_token_fn", None) if config else None
        if not callable(refresh_fn):
            skipped += 1
            continue

        try:
            refresh_fn(integration)
            refreshed += 1
            logger.info(
                "refresh_expiring_tokens: refreshed type=%s id=%s",
                integration.type,
                integration.id,
            )
        except Exception as exc:
            failed += 1
            logger.error(
                "refresh_expiring_tokens: failed type=%s id=%s err=%s",
                integration.type,
                integration.id,
                exc,
            )

    return {"refreshed": refreshed, "skipped": skipped, "failed": failed}
