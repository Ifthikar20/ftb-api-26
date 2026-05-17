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
