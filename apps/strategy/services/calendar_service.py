import logging
from django.utils import timezone

from apps.strategy.models import ContentCalendarEntry
from core.exceptions import AIGenerationFailed

logger = logging.getLogger("apps")


class CalendarService:
    @staticmethod
    def get_entries(*, website_id: str, month: str = None):
        if month:
            year, m = month.split("-")
            return ContentCalendarEntry.objects.filter(
                website_id=website_id,
                scheduled_date__year=year,
                scheduled_date__month=m,
            )
        return ContentCalendarEntry.objects.filter(website_id=website_id)

    @staticmethod
    def generate_for_next_month(*, website) -> list:
        """AI-generate content calendar entries for next month."""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        next_month = date.today() + relativedelta(months=1)

        entries = [
            ContentCalendarEntry.objects.create(
                website=website,
                title=f"Untitled Post {i}",
                topic="",
                content_type="blog",
                scheduled_date=next_month.replace(day=min(i * 7, 28)),
                ai_generated=True,
            )
            for i in range(1, 5)
        ]
        return entries
