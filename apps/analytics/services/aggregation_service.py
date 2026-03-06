import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger("apps")


class AggregationService:
    @staticmethod
    def aggregate_hourly(website_id: str = None):
        """Pre-aggregate hourly metrics for fast dashboard queries."""
        cutoff = timezone.now() - timedelta(hours=1)
        logger.info(f"Aggregating hourly metrics for website_id={website_id}")
        # Pre-aggregation logic would write to a dedicated analytics_hourly_aggregate table
