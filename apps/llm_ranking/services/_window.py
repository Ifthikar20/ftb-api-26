"""Resolve dashboard analytics filters to a (start, end) datetime window.

Centralises the parsing so KPI tiles, breakdowns, and the deep-dive
service all interpret query params identically.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

DEFAULT_DAYS = 30
# Sentinel for the "overall" range — a timestamp far enough in the past
# that any audit's completed_at falls inside the window. Picking the Unix
# epoch keeps the window finite for downstream span math.
EPOCH = timezone.make_aware(datetime(1970, 1, 1))

# Preset ranges expressed in days.
PRESET_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
}


def resolve_window(
    range_key: str | None,
    start: str | None,
    end: str | None,
) -> tuple[datetime, datetime]:
    """Return (start_dt, end_dt) for the requested analytics window.

    For "overall" the start is the Unix epoch so the query is effectively
    unbounded but downstream span math still works.
    """
    now = timezone.now()
    end_dt = _parse_dt(end, default=now, end_of_day=True) or now

    if range_key == "overall":
        return EPOCH, end_dt
    if range_key == "custom":
        start_dt = _parse_dt(start, default=now - timedelta(days=DEFAULT_DAYS))
        return start_dt, end_dt
    if range_key in PRESET_DAYS:
        return end_dt - timedelta(days=PRESET_DAYS[range_key]), end_dt
    return end_dt - timedelta(days=DEFAULT_DAYS), end_dt


def _parse_dt(value: str | None, *, default: datetime, end_of_day: bool = False) -> datetime:
    if not value:
        return default
    parsed = None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return default
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    if end_of_day and len(value) <= 10:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed


def parse_prompt_filter(raw) -> list[str] | None:
    """Normalise the raw prompts query param into a list, or None for unfiltered."""
    if raw is None:
        return None
    if isinstance(raw, str):
        items = [s for s in (p.strip() for p in raw.split("\n")) if s]
    elif isinstance(raw, list | tuple):
        items = [str(p).strip() for p in raw if str(p).strip()]
    else:
        return None
    return items or None


def parse_csv_filter(raw) -> list[str] | None:
    """Normalise ``?x=a,b`` or repeated ``?x=a&x=b`` into a list.

    Returns None for unfiltered so callers can pass the value straight
    through as a keyword argument default.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        parts = raw.split(",")
    elif isinstance(raw, list | tuple):
        parts = []
        for item in raw:
            parts.extend(str(item).split(","))
    else:
        return None
    items = [p.strip() for p in parts if p.strip()]
    return items or None


def apply_result_filters(qs, *, prompts=None, providers=None, tags=None, topics=None):
    """Apply the dashboard pill filters to an LLMRankingResult queryset.

    Single home for the filter semantics so the overview, KPI, breakdown
    and deep-dive builders can never drift apart. Tag and topic filters
    join through ``source_prompt`` — results without that link (legacy or
    custom prompts) fall outside those filters by construction; the
    dashboard surfaces the count rather than hiding it.
    """
    from django.db.models import F, Q

    if prompts:
        qs = qs.filter(prompt__in=prompts)
    if providers:
        qs = qs.filter(provider__in=providers)
    if topics:
        qs = qs.filter(source_prompt__industry__name__in=topics)
    if tags:
        # Tags live on BrandPrompt, which is per-website: scope the join to
        # the audit's own website so one tenant's tag names never match
        # another tenant's identical Prompt row.
        tag_q = Q()
        for tag in tags:
            tag_q |= Q(source_prompt__brand_prompts__tags__contains=[tag])
        qs = qs.filter(
            tag_q,
            source_prompt__brand_prompts__website_id=F("audit__website_id"),
        )
    if tags or topics:
        qs = qs.distinct()
    return qs
