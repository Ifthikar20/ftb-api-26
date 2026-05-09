"""ROI tracker — measures score lift attributed to a published draft.

After a draft is marked PUBLISHED, :func:`schedule_roi_measurement`
queues a Celery task ``days_after`` later. The task re-probes the
prompts referenced in the originating brief (when present) and persists
a :class:`ROIAttribution` row capturing visibility and citation deltas.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from apps.content_studio.models import ContentDraft, ROIAttribution

logger = logging.getLogger("apps")


def schedule_roi_measurement(draft_id: str, days_after: int = 14) -> None:
    """Queue ``measure_roi`` to run after ``days_after`` days."""
    try:
        from apps.content_studio.tasks import measure_roi
    except Exception:
        return
    eta = timezone.now() + timedelta(days=int(days_after))
    try:
        measure_roi.apply_async(args=[str(draft_id)], eta=eta)
    except Exception as exc:  # pragma: no cover
        logger.warning("schedule_roi_measurement(%s) failed: %s", draft_id, exc)


def _visibility_for_prompt(website, prompt_text: str, since=None) -> tuple[float, int]:
    """Return ``(mention_rate, citation_count)`` for a prompt over recent results."""
    try:
        from apps.llm_ranking.models import LLMRankingResult
    except Exception:
        return 0.0, 0
    qs = LLMRankingResult.objects.filter(audit__website=website, prompt=prompt_text)
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    total = qs.count()
    if not total:
        return 0.0, 0
    mentioned = qs.filter(is_mentioned=True).count()
    citation_count = 0
    try:
        from apps.citations.models import Citation  # type: ignore
        citation_count = Citation.objects.filter(
            result__in=qs, is_brand=True,
        ).count()
    except Exception:
        citation_count = 0
    return mentioned / total, citation_count


def measure_roi(draft_id: str) -> ROIAttribution | None:
    """Compute and persist a :class:`ROIAttribution` row for ``draft_id``."""
    try:
        draft = ContentDraft.objects.select_related("brief", "website").get(id=draft_id)
    except ContentDraft.DoesNotExist:
        return None

    publish_log = draft.publish_logs.filter(status="published").order_by("created_at").first()
    if publish_log is None:
        return None
    publish_time = publish_log.created_at
    now = timezone.now()
    days = max(0, (now - publish_time).days)

    brief = draft.brief
    affected_prompts: list[str] = []
    if brief and brief.target_prompt is not None:
        affected_prompts.append(str(brief.target_prompt.id))
        prompt_text = brief.target_prompt.text
    else:
        prompt_text = brief.headline if brief else ""

    before_rate, before_cites = _visibility_for_prompt(
        draft.website, prompt_text, since=publish_time - timedelta(days=14),
    )
    after_rate, after_cites = _visibility_for_prompt(
        draft.website, prompt_text, since=publish_time,
    )
    visibility_lift = (after_rate - before_rate) if (after_rate or before_rate) else None

    accuracy_lift = None
    if brief and brief.target_claim_mismatch is not None:
        try:
            mm = brief.target_claim_mismatch
            mm.refresh_from_db()
            accuracy_lift = 1.0 if mm.dismissed else 0.0
        except Exception:
            accuracy_lift = None

    return ROIAttribution.objects.create(
        draft=draft,
        website=draft.website,
        measured_at=now,
        days_since_publish=days,
        visibility_before=before_rate,
        visibility_after=after_rate,
        visibility_lift=visibility_lift,
        citation_count_before=before_cites,
        citation_count_after=after_cites,
        accuracy_lift=accuracy_lift,
        affected_prompts=affected_prompts,
    )
