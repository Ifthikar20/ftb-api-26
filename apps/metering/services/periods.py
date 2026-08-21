"""
The single definition of "the current usage window".

Every surface that windows AI usage — the spend wall, the cap
notifications, the Settings and Billing usage cards — calls
billing_period_for() so they can never disagree again.

Today no production user has a populated Subscription period (there are
no paying subscribers), so everyone falls back to the calendar month in
UTC. When the Phase 2 billing cutover starts populating
Subscription.current_period_start/end from Polar webhooks, every window
switches to real billing cycles automatically — no code change.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from core.utils.constants import SubscriptionStatus


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    source: str  # "subscription" | "calendar"

    @property
    def key(self) -> str:
        """Stable cache-key fragment for this window."""
        return self.start.date().isoformat()


def month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Calendar-month bounds in UTC (moved here from core.ai_tracking)."""
    now = now or timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return start, nxt


def billing_period_for(user) -> Period:
    """The user's current billing period, calendar month as fallback."""
    now = timezone.now()
    sub = getattr(user, "subscription", None) if user is not None else None
    if sub is not None:
        try:
            usable = (
                sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
                and sub.current_period_start is not None
                and sub.current_period_end is not None
                and sub.current_period_start <= now < sub.current_period_end
            )
        except Exception:
            usable = False
        if usable:
            return Period(
                start=sub.current_period_start,
                end=sub.current_period_end,
                source="subscription",
            )
    start, end = month_bounds(now)
    return Period(start=start, end=end, source="calendar")
