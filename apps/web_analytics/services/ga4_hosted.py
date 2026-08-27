"""
Hosted Google-tag source: per-website data streams in a FetchBot-owned
GA4 property.

The client pastes a standard gtag snippet (no Google account needed on
their side); events land in our pool property and are read back through
the Realtime API filtered to the website's stream. Only the stream ids
live in our DB (Integration.metadata) — the traffic data stays in
Google, snapshots stay in Redis.

Pool-property constraints, stated so nobody rediscovers them in prod:
  - GA4 caps a property at 50 data streams; provisioning surfaces
    "stream_limit_reached" instead of failing silently. Adding pool
    properties is future work.
  - Realtime API quota is per property, i.e. SHARED across every hosted
    website. The per-website DailyQuota in ga4_client plus the
    read-through snapshot TTL keep one tenant from draining the pool.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from django.conf import settings

from apps.web_analytics.services import ga4_client, ga4_service_account

logger = logging.getLogger("apps")

DATA_STREAMS_ENDPOINT = (
    "https://analyticsadmin.googleapis.com/v1beta/properties/{property_id}/dataStreams"
)

SNIPPET_TEMPLATE = (
    '<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>\n'
    "<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
    "gtag('js',new Date());gtag('config','{mid}');</script>"
)


def is_configured() -> bool:
    return ga4_service_account.is_configured()


def snippet(measurement_id: str) -> str:
    return SNIPPET_TEMPLATE.format(mid=measurement_id)


def get_integration(website):
    from apps.websites.models import Integration

    return Integration.objects.filter(website=website, type="ga_hosted").first()


def _display_name(website) -> str:
    host = urlparse(website.url).hostname or website.url
    # Suffix keeps names unique when two tenants track the same host.
    return f"{host} ({str(website.id)[:8]})"


def provision_stream(website):
    """Create (or reactivate) the website's stream in the pool property.

    Returns (integration, error_reason). error_reason is None on
    success, else one of "not_configured", "sa_token_failed",
    "stream_limit_reached", "provision_failed" — also persisted in
    metadata["provisioning_error"] for the status endpoint.
    """
    from apps.websites.models import Integration

    integration, _created = Integration.objects.get_or_create(
        website=website, type="ga_hosted"
    )
    metadata = dict(integration.metadata or {})

    if metadata.get("measurement_id") and metadata.get("stream_id"):
        metadata.pop("provisioning_error", None)
        integration.metadata = metadata
        integration.is_active = True
        integration.save(update_fields=["metadata", "is_active", "updated_at"])
        return integration, None

    def _fail(reason: str):
        metadata["provisioning_error"] = reason
        integration.metadata = metadata
        integration.is_active = False
        integration.save(update_fields=["metadata", "is_active", "updated_at"])
        return integration, reason

    if not is_configured():
        return _fail("not_configured")

    token = ga4_service_account.get_access_token()
    if not token:
        return _fail("sa_token_failed")

    property_id = str(settings.GA4_HOSTED_PROPERTY_ID)
    try:
        resp = requests.post(
            DATA_STREAMS_ENDPOINT.format(property_id=property_id),
            json={
                "type": "WEB_DATA_STREAM",
                "displayName": _display_name(website),
                "webStreamData": {"defaultUri": website.url},
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.warning("GA4 hosted stream create failed for %s: %s", website.id, exc)
        return _fail("provision_failed")

    if resp.status_code >= 400:
        detail = resp.text[:500]
        logger.warning(
            "GA4 hosted stream create rejected for %s (%s): %s",
            website.id, resp.status_code, detail,
        )
        if "limit" in detail.lower() or "maximum" in detail.lower():
            return _fail("stream_limit_reached")
        return _fail("provision_failed")

    try:
        data = resp.json()
    except ValueError:
        return _fail("provision_failed")

    measurement_id = (data.get("webStreamData") or {}).get("measurementId", "")
    stream_id = (data.get("name") or "").rsplit("/", 1)[-1]
    if not measurement_id or not stream_id:
        logger.warning("GA4 hosted stream create returned no ids for %s", website.id)
        return _fail("provision_failed")

    metadata.update(
        measurement_id=measurement_id,
        stream_id=stream_id,
        property_id=property_id,
    )
    metadata.pop("provisioning_error", None)
    integration.metadata = metadata
    integration.is_active = True
    integration.save(update_fields=["metadata", "is_active", "updated_at"])
    logger.info("GA4 hosted stream %s provisioned for website %s", stream_id, website.id)
    return integration, None


def disable(integration) -> None:
    """Delete the pool stream (best effort, frees one of the 50 slots)
    and deactivate the row."""
    metadata = dict(integration.metadata or {})
    stream_id = metadata.get("stream_id")
    property_id = metadata.get("property_id") or str(settings.GA4_HOSTED_PROPERTY_ID)

    if stream_id:
        token = ga4_service_account.get_access_token()
        if token:
            url = DATA_STREAMS_ENDPOINT.format(property_id=property_id) + f"/{stream_id}"
            try:
                requests.delete(
                    url, headers={"Authorization": f"Bearer {token}"}, timeout=15
                )
            except requests.RequestException as exc:
                logger.warning("GA4 hosted stream delete failed (ignored): %s", exc)

    metadata.pop("measurement_id", None)
    metadata.pop("stream_id", None)
    metadata.pop("provisioning_error", None)
    integration.metadata = metadata
    integration.is_active = False
    integration.save(update_fields=["metadata", "is_active", "updated_at"])


def build_hosted_snapshot(website, integration) -> dict | None:
    """Realtime snapshot for one hosted stream, or None (serve stale)."""
    stream_id = (integration.metadata or {}).get("stream_id")
    if not stream_id:
        return None
    token = ga4_service_account.get_access_token()
    if not token:
        return None
    property_id = (integration.metadata or {}).get("property_id") or str(
        settings.GA4_HOSTED_PROPERTY_ID
    )
    return ga4_client.build_realtime_snapshot(
        token,
        property_id,
        website_id=str(website.id),
        dimension_filter=ga4_client.stream_filter(stream_id),
        source="ga_hosted",
    )
