import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.leads.tasks.rescore_all_leads")
def rescore_all_leads():
    """Nightly task to rescore all leads across all websites."""
    from apps.websites.models import Website
    from apps.leads.services.scoring_service import ScoringService

    for website in Website.objects.filter(is_active=True):
        try:
            count = ScoringService.rescore_website(website_id=str(website.id))
            logger.info(f"Rescored {count} visitors for website {website.id}")
        except Exception as e:
            logger.error(f"Rescoring failed for website {website.id}: {e}")
