"""Celery tasks for the content_studio app."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.content_studio.tasks.generate_briefs_for_website")
def generate_briefs_for_website(website_id: str) -> int:
    from apps.content_studio.services.brief_generator import (
        generate_briefs_for_website as _impl,
    )
    try:
        return _impl(website_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("generate_briefs_for_website(%s) failed: %s", website_id, exc)
        return 0


@shared_task(name="apps.content_studio.tasks.generate_briefs_daily")
def generate_briefs_daily() -> int:
    """Iterate active websites and queue per-site brief generation."""
    try:
        from apps.websites.models import Website
    except Exception:
        return 0
    qs = Website.objects.filter(is_active=True).values_list("id", flat=True)
    count = 0
    for wid in qs:
        generate_briefs_for_website.delay(str(wid))
        count += 1
    return count


@shared_task(name="apps.content_studio.tasks.draft_content")
def draft_content(brief_id: str) -> str:
    from apps.content_studio.services.drafter import draft_content as _impl
    try:
        draft = _impl(brief_id)
        return str(draft.id)
    except Exception as exc:  # pragma: no cover
        logger.exception("draft_content(%s) failed: %s", brief_id, exc)
        return ""


@shared_task(name="apps.content_studio.tasks.publish_draft")
def publish_draft(draft_id: str, target_id: str) -> str:
    from apps.content_studio.models import (
        ContentDraft,
        DraftStatus,
        PublishLog,
        PublishStatus,
        PublishTarget,
    )
    from apps.content_studio.services.publish_adapters import get_adapter
    from apps.content_studio.services.roi_tracker import schedule_roi_measurement

    try:
        draft = ContentDraft.objects.get(id=draft_id)
        target = PublishTarget.objects.get(id=target_id)
    except (ContentDraft.DoesNotExist, PublishTarget.DoesNotExist):
        return ""

    adapter = get_adapter(target.provider)
    result = adapter.publish(draft, target)

    log = PublishLog.objects.create(
        draft=draft,
        target=target,
        status=result.get("status", PublishStatus.FAILED.value),
        external_id=result.get("external_id", "") or "",
        external_url=result.get("external_url", "") or "",
        error_message=result.get("error_message", "") or "",
        request_payload=result.get("request_payload") or {},
        response_payload=result.get("response_payload") or {},
    )

    if log.status == PublishStatus.PUBLISHED.value:
        draft.status = DraftStatus.PUBLISHED.value
        draft.save(update_fields=["status", "updated_at"])
        schedule_roi_measurement(str(draft.id))
    return str(log.id)


@shared_task(name="apps.content_studio.tasks.measure_roi")
def measure_roi(draft_id: str) -> str:
    from apps.content_studio.services.roi_tracker import measure_roi as _impl
    try:
        row = _impl(draft_id)
        return str(row.id) if row is not None else ""
    except Exception as exc:  # pragma: no cover
        logger.exception("measure_roi(%s) failed: %s", draft_id, exc)
        return ""
