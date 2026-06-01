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
MONTH12_BUCKETS = 12


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
        "month12": _month12_series(user, now),
    }


def build_month12_for_website(user, website) -> dict:
    """Return a 12-month visibility series scoped to a single website.

    Used by the dashboard's Visibility Overview card. Unlike ``build_for_user``,
    this always returns a series — empty buckets are zero, not None — so the
    chart renders even when only a few months have data.
    """
    now = timezone.now()
    return _month12_series(user, now, website=website)


def build_overview_for_website(user, website) -> dict:
    """Return the Visibility Overview payload for a single website.

    Combines the 12-month brand + competitor series with computed headline
    values and trend deltas so the dashboard card doesn't have to derive
    them client-side.

    Delta formula: mean of the last three months vs the prior three months,
    expressed as a percentage change of the prior window. Falls back to a
    first-vs-last calculation when the series has fewer than six populated
    points. Always returns the chart series; ``has_data`` is False when
    every bucket is zero so the card can show its sample-data badge.
    """
    series = build_month12_for_website(user, website)
    brand = series["brand"]
    competitor = series["competitor"]

    has_data = any(v > 0 for v in brand) or any(v > 0 for v in competitor)

    return {
        "labels": series["labels"],
        "brand": brand,
        "competitor": competitor,
        "brand_current": _current(brand),
        "competitor_current": _current(competitor),
        "brand_delta_pct": _trend_delta(brand),
        "competitor_delta_pct": _trend_delta(competitor),
        "has_data": has_data,
    }


def _current(series: list[float]) -> float:
    """Most recent populated value, or the very last value if all are zero."""
    if not series:
        return 0.0
    for value in reversed(series):
        if value:
            return round(value, 1)
    return round(series[-1], 1)


def _trend_delta(series: list[float]) -> float:
    """Percent change of the last 3-mo mean vs the prior 3-mo mean."""
    if not series or len(series) < 2:
        return 0.0
    if len(series) >= 6:
        tail = series[-3:]
        prev = series[-6:-3]
        tail_avg = sum(tail) / len(tail)
        prev_avg = sum(prev) / len(prev)
        if prev_avg == 0:
            return 0.0
        return round((tail_avg - prev_avg) / prev_avg * 100, 1)
    first = series[0] or 1
    last = series[-1]
    return round((last - first) / abs(first) * 100, 1)


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


def _month12_series(user, now: datetime, *, website=None) -> dict:
    months = _last_n_month_starts(now.date(), MONTH12_BUCKETS)
    labels = [m.strftime("%b") for m in months]
    ranges = [
        (_start_of_day(m), _start_of_day(_first_of_next_month(m)))
        for m in months
    ]
    return _series_for_ranges(user, labels, ranges, website=website)


# ── core aggregation ────────────────────────────────────────────────────────

def _series_for_ranges(
    user, labels: list[str], ranges: list[tuple[datetime, datetime]],
    *, website=None,
) -> dict:
    """Compute brand + competitor rates for each (start, end) range.

    Both rates are expressed in percent (0-100) so the chart axis stays
    consistent with the existing tooltip format. When ``website`` is given,
    the audit filter is restricted to that website only.
    """
    brand: list[float] = []
    competitor: list[float] = []
    for start, end in ranges:
        qs = LLMRankingAudit.objects.filter(
            created_by=user,
            status=LLMRankingAudit.STATUS_COMPLETED,
            completed_at__gte=start,
            completed_at__lt=end,
        )
        if website is not None:
            qs = qs.filter(website=website)
        audit_ids = list(qs.values_list("id", flat=True))
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
