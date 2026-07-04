"""
Nightly Search Analytics ingestion.

Pulls three dimension slices per website (date, date+query, date+page)
and upserts them into the search_console tables. Sync windows always
end 3 days before today because GSC finalizes data with a lag; the
incremental window re-pulls the last GSC_SYNC_LOOKBACK_DAYS because
Google revises recent days, and the upserts make that idempotent.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from apps.search_console.models import GscDailyTotal, GscPageStat, GscQueryStat
from apps.search_console.services import gsc_client, oauth_service

logger = logging.getLogger("apps")

# GSC data for the most recent days is incomplete; stay behind the lag.
DATA_LAG_DAYS = 3

MAX_QUERY_LENGTH = 512
MAX_PAGE_LENGTH = 1000

_METRIC_FIELDS = ["clicks", "impressions", "ctr", "position"]


def compute_sync_window(integration, today: date | None = None) -> tuple[date, date]:
    """Return (start, end) dates for the next sync of this integration."""
    today = today or timezone.now().date()
    end = today - timedelta(days=DATA_LAG_DAYS)

    is_first_sync = (
        integration.last_synced_at is None
        and not GscDailyTotal.objects.filter(website=integration.website).exists()
    )
    if is_first_sync:
        days = int(getattr(settings, "GSC_BACKFILL_DAYS", 28))
    else:
        days = int(getattr(settings, "GSC_SYNC_LOOKBACK_DAYS", 7))
    start = end - timedelta(days=days - 1)
    return start, end


def _upsert(model, website, rows: list[dict], *, key_field: str | None = None) -> int:
    """Bulk upsert Google rows into one of the Gsc* tables.

    Google rows look like {"keys": ["2026-06-01", "some query"],
    "clicks": .., "impressions": .., "ctr": .., "position": ..} with
    keys ordered like the requested dimensions (date first).
    """
    instances = []
    seen: set[tuple] = set()
    for row in rows:
        keys = row.get("keys") or []
        if not keys:
            continue
        kwargs = {
            "website": website,
            "date": keys[0],
            "clicks": int(row.get("clicks") or 0),
            "impressions": int(row.get("impressions") or 0),
            "ctr": float(row.get("ctr") or 0.0),
            "position": float(row.get("position") or 0.0),
        }
        if key_field:
            if len(keys) < 2 or not keys[1]:
                continue
            max_len = MAX_QUERY_LENGTH if key_field == "query" else MAX_PAGE_LENGTH
            kwargs[key_field] = str(keys[1])[:max_len]
            dedup_key = (keys[0], kwargs[key_field])
        else:
            dedup_key = (keys[0],)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        instances.append(model(**kwargs))

    if not instances:
        return 0

    unique_fields = ["website", "date"] + ([key_field] if key_field else [])
    model.objects.bulk_create(
        instances,
        update_conflicts=True,
        unique_fields=unique_fields,
        update_fields=_METRIC_FIELDS + ["updated_at"],
        batch_size=1000,
    )
    return len(instances)


def sync_window(integration, *, start_date: date, end_date: date) -> dict:
    """Pull and store all three dimension slices for one window."""
    site_url = (integration.metadata or {}).get("site_url")
    if not site_url:
        logger.warning(
            "GSC integration %s has no site_url selected; skipping sync",
            integration.pk,
        )
        return {"skipped": "no_site_url"}

    if integration.needs_token_refresh():
        oauth_service.refresh_access_token(integration)
        integration.refresh_from_db()
        if not integration.is_active:
            return {"skipped": "revoked"}

    website = integration.website
    user_id = website.user_id
    stats: dict = {}
    common = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "user_id": user_id,
        "stats": stats,
    }

    totals = gsc_client.query_all_rows(
        integration.access_token, site_url, dimensions=["date"], **common
    )
    queries = gsc_client.query_all_rows(
        integration.access_token, site_url, dimensions=["date", "query"], **common
    )
    pages = gsc_client.query_all_rows(
        integration.access_token, site_url, dimensions=["date", "page"], **common
    )

    result = {
        "totals": _upsert(GscDailyTotal, website, totals),
        "queries": _upsert(GscQueryStat, website, queries, key_field="query"),
        "pages": _upsert(GscPageStat, website, pages, key_field="page"),
        **stats,
    }

    integration.last_synced_at = timezone.now()
    integration.save(update_fields=["last_synced_at", "updated_at"])
    logger.info("GSC sync for website %s: %s", website.pk, result)
    return result


def prune_old_rows(website) -> int:
    """Delete rows older than the retention window. Returns count deleted."""
    cutoff = timezone.now().date() - timedelta(
        days=int(getattr(settings, "GSC_RETENTION_DAYS", 480))
    )
    deleted = 0
    for model in (GscDailyTotal, GscQueryStat, GscPageStat):
        count, _ = model.objects.filter(website=website, date__lt=cutoff).delete()
        deleted += count
    return deleted
