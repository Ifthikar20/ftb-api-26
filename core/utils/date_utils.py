from datetime import datetime, timedelta

import pytz
from django.utils import timezone


def get_date_range(period: str, start_date=None, end_date=None) -> tuple[datetime, datetime]:
    """Parse a period string into start/end datetimes."""
    now = timezone.now()

    if period == "today" or period == "24h":
        start = now - timedelta(hours=24)
        end = now
    elif period == "7d":
        start = now - timedelta(days=7)
        end = now
    elif period == "30d":
        start = now - timedelta(days=30)
        end = now
    elif period == "90d":
        start = now - timedelta(days=90)
        end = now
    elif period == "custom" and start_date and end_date:
        start = datetime.fromisoformat(start_date).replace(tzinfo=pytz.UTC)
        end = datetime.fromisoformat(end_date).replace(tzinfo=pytz.UTC)
    else:
        start = now - timedelta(days=30)
        end = now

    return start, end


def to_user_timezone(dt: datetime, user_tz: str) -> datetime:
    """Convert UTC datetime to user's local timezone."""
    user_timezone = pytz.timezone(user_tz)
    return dt.astimezone(user_timezone)
