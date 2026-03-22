import logging

from django.utils import timezone

from apps.competitors.models import Competitor, CompetitorSnapshot

logger = logging.getLogger("apps")


class CrawlService:
    @staticmethod
    def crawl_competitor(*, competitor: Competitor) -> CompetitorSnapshot:
        """Crawl a competitor's website and capture metrics."""
        logger.info(f"Crawling competitor: {competitor.competitor_url}")

        # This would use DataForSEO, Ahrefs API, or similar
        snapshot = CompetitorSnapshot.objects.create(
            competitor=competitor,
            captured_at=timezone.now(),
            metrics={},
        )

        competitor.last_crawled_at = timezone.now()
        competitor.save(update_fields=["last_crawled_at"])

        return snapshot
