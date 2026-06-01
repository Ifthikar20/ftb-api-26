"""Visibility-over-time series builder for the dashboard chart.

Aggregates a user's completed LLM ranking audits into bucketed series
(day / week / month) suitable for the frontend `VisibilityChart` component.

Shape returned:
    {
        "day":   {"labels": [...], "brand": [...], "competitor": [...]},
        "week":  {"labels": [...], "brand": [...], "competitor": [...]},
        "month": {"labels": [...], "brand": [...], "competitor": [...]},
    }

If the user has zero completed audits, returns None — the frontend renders
its empty state in that case.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from django.utils import timezone

from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

DAY_BUCKETS = 7
WEEK_BUCKETS = 8
MONTH_BUCKETS = 6


def build_for_user(user) -> dict | None:
    """Return the bundled visibility series for a user, or None if no data."""
    has_any = LLMRankingAudit.objects.filter(
        created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
    ).exists()
    if not has_any:
        return None
    now = timezone.now()
    return {
        "day": _day_series(user, now),
        "week": _week_series(user, now),
        "month": _month_series(user, now),
    }


# ── bucket builders ─────────────────────────────────────────────────────────

def _day_series(user, now: datetime) -> dict:
    today = now.date()
    buckets = [today - timedelta(days=i) for i in range(DAY_BUCKETS - 1, -1, -1)]
    labels = [d.strftime("%a") for d in buckets]
    ranges = [(_start_of_day(d), _start_of_day(d) + timedelta(days=1)) for d in buckets]
    return _series_for_ranges(user, labels, ranges)


def _week_series(user, now: datetime) -> dict:
    # Anchor on Monday of the current week, walk back WEEK_BUCKETS - 1 weeks.
    monday = now.date() - timedelta(days=now.weekday())
    starts = [monday - timedelta(weeks=i) for i in range(WEEK_BUCKETS - 1, -1, -1)]
    labels = [f"W{i + 1}" for i in range(WEEK_BUCKETS)]
    ranges = [(_start_of_day(s), _start_of_day(s) + timedelta(weeks=1)) for s in starts]
    return _series_for_ranges(user, labels, ranges)


def _month_series(user, now: datetime) -> dict:
    months = _last_n_month_starts(now.date(), MONTH_BUCKETS)
    labels = [m.strftime("%b") for m in months]
    ranges = [
        (_start_of_day(m), _start_of_day(_first_of_next_month(m)))
        for m in months
    ]
    return _series_for_ranges(user, labels, ranges)


# ── core aggregation ────────────────────────────────────────────────────────

def _series_for_ranges(
    user, labels: list[str], ranges: list[tuple[datetime, datetime]],
) -> dict:
    """Compute brand + competitor rates for each (start, end) range.

    Both rates are expressed in percent (0-100) so the chart axis stays
    consistent with the existing tooltip format.
    """
    brand: list[float] = []
    competitor: list[float] = []
    for start, end in ranges:
        audit_ids = list(
            LLMRankingAudit.objects.filter(
                created_by=user,
                status=LLMRankingAudit.STATUS_COMPLETED,
                completed_at__gte=start,
                completed_at__lt=end,
            ).values_list("id", flat=True)
        )
        brand.append(_brand_rate(audit_ids))
        competitor.append(_competitor_rate(audit_ids))
    return {"labels": labels, "brand": brand, "competitor": competitor}


def _brand_rate(audit_ids: list) -> float:
    """Average mention_rate across this bucket's audits, in percent."""
    if not audit_ids:
        return 0.0
    audits = LLMRankingAudit.objects.filter(id__in=audit_ids)
    rates = [a.mention_rate for a in audits if a.mention_rate is not None]
    if not rates:
        return 0.0
    return round(sum(rates) / len(rates), 1)


def _competitor_rate(audit_ids: list) -> float:
    """Share of successful AI answers in this bucket that mention any competitor."""
    if not audit_ids:
        return 0.0
    succeeded = LLMRankingResult.objects.filter(
        audit_id__in=audit_ids, query_succeeded=True,
    )
    total = succeeded.count()
    if total == 0:
        return 0.0
    with_competitors = sum(
        1 for row in succeeded.only("competitors_mentioned")
        if _has_competitor(row.competitors_mentioned)
    )
    return round(100.0 * with_competitors / total, 1)


def _has_competitor(value) -> bool:
    """Treat any non-empty competitors_mentioned entry as 'mentions a competitor'."""
    if not value:
        return False
    if isinstance(value, list):
        return any(
            (isinstance(item, str) and item.strip())
            or (isinstance(item, dict) and item.get("name"))
            for item in value
        )
    return False


# ── date helpers ────────────────────────────────────────────────────────────

def _start_of_day(d: date) -> datetime:
    return timezone.make_aware(datetime(d.year, d.month, d.day))


def _first_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def _first_of_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _last_n_month_starts(today: date, n: int) -> list[date]:
    current = _first_of_month(today)
    months: list[date] = []
    for _ in range(n):
        months.append(current)
        # Step back one month.
        if current.month == 1:
            current = date(current.year - 1, 12, 1)
        else:
            current = date(current.year, current.month - 1, 1)
    return list(reversed(months))
