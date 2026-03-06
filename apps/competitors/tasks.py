import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.competitors.tasks.crawl_all_competitors")
def crawl_all_competitors():
    """Weekly task to crawl all tracked competitors."""
    from apps.competitors.models import Competitor
    from apps.competitors.services.crawl_service import CrawlService
    from apps.competitors.services.change_detection_service import ChangeDetectionService

    for competitor in Competitor.objects.select_related("website"):
        try:
            CrawlService.crawl_competitor(competitor=competitor)
            ChangeDetectionService.detect_changes(competitor=competitor)
        except Exception as e:
            logger.error(f"Crawl failed for competitor {competitor.id}: {e}")
