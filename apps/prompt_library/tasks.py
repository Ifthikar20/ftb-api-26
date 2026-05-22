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


@shared_task(name="apps.prompt_library.tasks.refresh_effectiveness_scores")
def refresh_effectiveness_scores() -> int:
    """Refresh effectiveness_score for every active prompt.

    Pulls from ``LLMRankingResult`` rows linked via the ``source_prompt``
    foreign key. See :mod:`apps.prompt_library.services.effectiveness`.
    """
    from apps.prompt_library.services.effectiveness import (
        refresh_all_effectiveness_scores,
    )

    return refresh_all_effectiveness_scores()


@shared_task(name="apps.prompt_library.tasks.crawl_prompt_for_website",
             bind=True, max_retries=0)
def crawl_prompt_for_website(self, website_id: str, prompt_id: str) -> dict:
    """Fan out + query providers for a single saved prompt.

    Invoked from the Prompt-detail page's 'Run crawler' button. We
    don't retry on failure — the crawler service updates the
    PromptCrawlRun row with whatever it managed to capture, so the
    UI can show partial results plus per-provider error notes.
    """
    from apps.prompt_library.models import Prompt
    from apps.prompt_library.services.prompt_crawler import crawl_prompt
    from apps.websites.models import Website

    try:
        website = Website.objects.get(id=website_id)
        prompt = Prompt.objects.get(id=prompt_id)
    except (Website.DoesNotExist, Prompt.DoesNotExist) as exc:
        logger.warning("crawl_prompt_for_website: %s", exc)
        return {"ok": False, "error": str(exc)}

    outcome = crawl_prompt(website, prompt)
    return {
        "ok": True,
        "fanouts": len(outcome.fanouts),
        "responses": outcome.responses,
        "errors": outcome.errors,
    }
