import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.analytics.tasks.aggregate_hourly_metrics")
def aggregate_hourly_metrics():
    """Pre-aggregate hourly analytics data."""
    from apps.websites.models import Website
    from apps.analytics.services.aggregation_service import AggregationService

    for website in Website.objects.filter(is_active=True):
        try:
            AggregationService.aggregate_hourly(website_id=str(website.id))
        except Exception as e:
            logger.error(f"Aggregation failed for website {website.id}: {e}")
