"""Search Console Celery tasks."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.search_console.tasks.sync_all_gsc")
def sync_all_gsc() -> int:
    """Nightly dispatcher: one sync task per connected GSC integration."""
    from apps.websites.models import Integration

    dispatched = 0
    integrations = Integration.objects.filter(type="gsc", is_active=True)
    for integration in integrations:
        if not (integration.metadata or {}).get("site_url"):
            continue
        sync_website_gsc.delay(integration_id=integration.pk)
        dispatched += 1
    logger.info("sync_all_gsc dispatched %d syncs", dispatched)
    return dispatched


@shared_task(
    name="apps.search_console.tasks.sync_website_gsc",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def sync_website_gsc(self, integration_id, backfill_days: int | None = None) -> dict:
    """Sync one website's Search Analytics data, then feed the prompt library.

    backfill_days overrides the computed window; it is passed right
    after a connection or property selection to pull initial history.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from apps.search_console.services import ingestion_service
    from apps.search_console.services.prompt_feed import feed_prompts_for_website
    from apps.websites.models import Integration

    try:
        integration = Integration.objects.select_related("website").get(
            pk=integration_id, type="gsc", is_active=True
        )
    except Integration.DoesNotExist:
        logger.warning("sync_website_gsc: integration %s not found or inactive", integration_id)
        return {"skipped": "not_found"}

    try:
        if backfill_days:
            end = timezone.now().date() - timedelta(days=ingestion_service.DATA_LAG_DAYS)
            start = end - timedelta(days=int(backfill_days) - 1)
        else:
            start, end = ingestion_service.compute_sync_window(integration)
        result = ingestion_service.sync_window(
            integration, start_date=start, end_date=end
        )
        ingestion_service.prune_old_rows(integration.website)
    except Exception as exc:
        logger.exception("sync_website_gsc(%s) failed: %s", integration_id, exc)
        raise self.retry(exc=exc) from exc

    try:
        feed_days = int(getattr(settings, "GSC_BACKFILL_DAYS", 28))
        result["prompt_feed"] = feed_prompts_for_website(
            integration.website, days=feed_days
        )
    except Exception as exc:  # pragma: no cover
        logger.exception(
            "GSC prompt feed failed for website %s: %s", integration.website_id, exc
        )
        result["prompt_feed"] = {"error": str(exc)}

    return result
