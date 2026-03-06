import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.strategy.tasks.generate_strategy_async")
def generate_strategy_async(website_id: str, plan_type: str = "30"):
    """Asynchronously generate an AI growth strategy."""
    from apps.websites.models import Website
    from apps.strategy.services.strategy_generator import StrategyGenerator

    try:
        website = Website.objects.get(id=website_id)
        StrategyGenerator.generate(website=website, plan_type=plan_type)
        logger.info(f"Strategy generated for website {website_id}")
    except Exception as e:
        logger.error(f"Strategy generation failed for {website_id}: {e}")


@shared_task(name="apps.strategy.tasks.generate_morning_briefs")
def generate_morning_briefs():
    """Generate daily morning briefs for all active websites."""
    from apps.websites.models import Website
    from apps.strategy.services.morning_brief_service import MorningBriefService

    for website in Website.objects.filter(is_active=True, pixel_verified=True):
        try:
            MorningBriefService.generate_brief(website=website)
        except Exception as e:
            logger.error(f"Morning brief failed for website {website.id}: {e}")
