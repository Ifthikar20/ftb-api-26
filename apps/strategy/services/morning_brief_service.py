import logging
from django.conf import settings
from django.utils import timezone

from apps.strategy.models import MorningBrief
from core.exceptions import AIGenerationFailed

logger = logging.getLogger("apps")


class MorningBriefService:
    @staticmethod
    def generate_brief(*, website) -> MorningBrief:
        """Generate today's AI morning brief."""
        today = timezone.now().date()

        existing = MorningBrief.objects.filter(website=website, date=today).first()
        if existing:
            return existing

        metrics = MorningBriefService._get_metrics_snapshot(website=website)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": f"""Generate a concise morning brief for {website.name} ({website.url}).

Yesterday's metrics:
{metrics}

Provide:
1. 3 key insights from yesterday's data
2. Top priority for today
3. One quick win to implement

Keep it under 200 words, punchy and actionable."""
                }],
            )
            content = response.content[0].text
        except Exception as e:
            logger.error(f"Morning brief generation failed: {e}")
            content = f"Morning brief for {website.name} — {today}. Check your analytics dashboard for today's insights."

        brief = MorningBrief.objects.create(
            website=website,
            date=today,
            content=content,
            metrics_snapshot=metrics,
        )
        return brief

    @staticmethod
    def _get_metrics_snapshot(*, website) -> dict:
        from apps.analytics.services.analytics_service import AnalyticsService
        try:
            return AnalyticsService.get_overview(website_id=str(website.id), period="today")
        except Exception:
            return {}
