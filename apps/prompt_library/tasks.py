"""Celery tasks for the prompt library."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.prompt_library.tasks.mine_daily_prompts")
def mine_daily_prompts(industry_slug: str | None = None) -> dict:
    """Run all configured miners against one or every active industry."""
    from apps.prompt_library.models import Industry
    from apps.prompt_library.services.miner_service import mine_for_industry

    qs = Industry.objects.filter(is_active=True)
    if industry_slug:
        qs = qs.filter(slug=industry_slug)
    summary: dict[str, dict] = {}
    for industry in qs:
        try:
            summary[industry.slug] = mine_for_industry(industry)
        except Exception as exc:  # pragma: no cover
            logger.exception("mine_daily_prompts failed for %s: %s", industry.slug, exc)
            summary[industry.slug] = {"error": str(exc)}
    return summary


@shared_task(name="apps.prompt_library.tasks.compute_demand_scores")
def compute_demand_scores() -> int:
    """Refresh demand_score for every active prompt."""
    from apps.prompt_library.services.scoring_service import refresh_all_scores

    return refresh_all_scores()
