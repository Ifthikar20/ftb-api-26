import logging

from apps.competitors.models import Competitor

logger = logging.getLogger("apps")


class DiscoveryService:
    @staticmethod
    def auto_detect(*, website) -> list:
        """Use AI/data APIs to discover competitors for a website."""
        # This would integrate with DataForSEO or similar APIs
        # Placeholder returns empty list
        logger.info(f"Auto-detecting competitors for {website.url}")
        return []

    @staticmethod
    def add_competitor(*, website, competitor_url: str, name: str = "") -> Competitor:
        """Manually add a competitor to track."""
        from core.exceptions import CompetitorLimitReached
        from core.permissions.feature_flags import get_competitor_limit

        limit = get_competitor_limit(website.user)
        current = Competitor.objects.filter(website=website).count()
        if current >= limit:
            raise CompetitorLimitReached()

        competitor, created = Competitor.objects.get_or_create(
            website=website,
            competitor_url=competitor_url,
            defaults={"name": name or competitor_url},
        )
        return competitor
