"""GEO KPI tiles for the dashboard Analytics tab.

Builds the three top-line metrics the product surfaces:

- Visibility — share of AI answers that mention the brand
- Position   — average rank when mentioned (lower is better)
- Sentiment  — net sentiment score (0-100) across mentioned answers

Each tile compares the user's last PERIOD_DAYS of completed audits
against the PERIOD_DAYS before that, so the chart never claims a trend
on a single audit.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.utils import timezone

from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

PERIOD_DAYS = 30


def build_kpis_for_user(
    user,
    *,
    start: Optional["datetime"] = None,
    end: Optional["datetime"] = None,
    prompts: Optional[list[str]] = None,
) -> list[dict] | None:
    """Return Visibility / Position / Sentiment tiles for the given window.

    When start is None the window is unbounded on the lower side (treated
    as "overall"). When prompts is provided the metrics are recomputed
    per-result so the filter actually narrows the cells we count.
    """
    has_any = LLMRankingAudit.objects.filter(
        created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
    ).exists()
    if not has_any:
        return None

    end = end or timezone.now()
    if start is None:
        # Default window: last PERIOD_DAYS. "Overall" callers supply
        # start explicitly (via resolve_window) so this only runs when
        # the caller passes no filter.
        start_current = end - timedelta(days=PERIOD_DAYS)
    else:
        start_current = start

    span = end - start_current
    if span.total_seconds() <= 0:
        span = timedelta(days=PERIOD_DAYS)
    current = (start_current, end)
    previous = (start_current - span, start_current)

    return [
        _build_tile(
            label="Visibility",
            subtext=(
                "See the share of chats where your brand is mentioned and "
                "understand how often you show up in conversations."
            ),
            higher_better=True,
            value_fmt=_pct,
            current=_visibility(user, *current, prompts=prompts),
            previous=_visibility(user, *previous, prompts=prompts),
        ),
        _build_tile(
            label="Position",
            subtext=(
                "Understand your brand's position within AI search results "
                "and uncover opportunities to improve your ranking."
            ),
            higher_better=False,
            value_fmt=_rank,
            current=_position(user, *current, prompts=prompts),
            previous=_position(user, *previous, prompts=prompts),
        ),
        _build_tile(
            label="Sentiment",
            subtext=(
                "Find out how your brand is perceived by AI, what's going "
                "well, and what requires improvements."
            ),
            higher_better=True,
            value_fmt=_score,
            current=_sentiment(user, *current, prompts=prompts),
            previous=_sentiment(user, *previous, prompts=prompts),
        ),
    ]


# ── Breakdown payload for the per-metric detail cards ──────────────────────

def build_breakdowns_for_user(
    user,
    *,
    start=None,
    end=None,
    prompts: Optional[list[str]] = None,
) -> dict | None:
    """Return per-metric drill-downs for the dashboard, or None if no data."""
    end = end or timezone.now()
    if start is None:
        start = (
            LLMRankingAudit.objects
            .filter(created_by=user, status=LLMRankingAudit.STATUS_COMPLETED)
            .order_by("completed_at")
            .values_list("completed_at", flat=True)
            .first()
        )
    audit_ids = list(_audits_in(user, start, end).values_list("id", flat=True))
    if not audit_ids:
        return None
    return {
        "visibility": _visibility_breakdown(audit_ids, prompts),
        "position": _position_breakdown(audit_ids, prompts),
        "sentiment": _sentiment_breakdown(audit_ids, prompts),
    }


def _visibility_breakdown(audit_ids: list, prompts: Optional[list[str]]) -> dict:
    """Mention share per LLM provider in the window."""
    rows: dict[str, dict[str, int]] = {}
    for r in _filtered_results(audit_ids, prompts).values("provider", "is_mentioned"):
        bucket = rows.setdefault(r["provider"], {"total": 0, "mentions": 0})
        bucket["total"] += 1
        if r["is_mentioned"]:
            bucket["mentions"] += 1
    providers = [
        {
            "provider": p,
            "mentions": v["mentions"],
            "total": v["total"],
            "mention_rate": round(100.0 * v["mentions"] / v["total"], 1) if v["total"] else 0.0,
        }
        for p, v in rows.items()
    ]
    providers.sort(key=lambda x: x["mention_rate"], reverse=True)
    return {"by_provider": providers}


def _position_breakdown(audit_ids: list, prompts: Optional[list[str]]) -> dict:
    """Distribution of mention rank across the window."""
    buckets = {"1": 0, "2-3": 0, "4-10": 0, "11+": 0}
    qs = (
        _filtered_results(audit_ids, prompts)
        .filter(is_mentioned=True, mention_rank__isnull=False)
        .values_list("mention_rank", flat=True)
    )
    total = 0
    for rank in qs:
        total += 1
        if rank == 1:
            buckets["1"] += 1
        elif rank <= 3:
            buckets["2-3"] += 1
        elif rank <= 10:
            buckets["4-10"] += 1
        else:
            buckets["11+"] += 1
    distribution = [
        {
            "range": label,
            "count": count,
            "pct": round(100.0 * count / total, 1) if total else 0.0,
        }
        for label, count in buckets.items()
    ]
    return {"distribution": distribution, "total_mentions": total}


def _sentiment_breakdown(audit_ids: list, prompts: Optional[list[str]]) -> dict:
    """Positive/neutral/negative split plus a few representative quotes."""
    qs = _filtered_results(audit_ids, prompts).filter(is_mentioned=True)
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for s in qs.values_list("sentiment", flat=True):
        if s in counts:
            counts[s] += 1
    total = sum(counts.values())
    split = [
        {
            "sentiment": k,
            "count": v,
            "pct": round(100.0 * v / total, 1) if total else 0.0,
        }
        for k, v in counts.items()
    ]
    samples = []
    for sentiment in (
        LLMRankingResult.SENTIMENT_POSITIVE,
        LLMRankingResult.SENTIMENT_NEGATIVE,
    ):
        row = (
            qs.filter(sentiment=sentiment)
            .exclude(mention_context="")
            .order_by("-confidence_score")
            .values("sentiment", "provider", "mention_context")
            .first()
        )
        if row:
            samples.append({
                "sentiment": row["sentiment"],
                "provider": row["provider"],
                "quote": row["mention_context"][:280],
            })
    return {"split": split, "samples": samples, "total_mentions": total}


# ── metric calculators ─────────────────────────────────────────────────────

def _audits_in(user, start, end):
    qs = LLMRankingAudit.objects.filter(
        created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
    )
    if start is not None:
        qs = qs.filter(completed_at__gte=start)
    if end is not None:
        qs = qs.filter(completed_at__lt=end)
    return qs


def _filtered_results(audit_ids, prompts):
    qs = LLMRankingResult.objects.filter(
        audit_id__in=audit_ids, query_succeeded=True,
    )
    if prompts:
        qs = qs.filter(prompt__in=prompts)
    return qs


def _visibility(user, start, end, *, prompts=None) -> float | None:
    if start is None and end is None:
        return None
    if prompts:
        audit_ids = list(_audits_in(user, start, end).values_list("id", flat=True))
        if not audit_ids:
            return None
        qs = _filtered_results(audit_ids, prompts)
        total = qs.count()
        if total == 0:
            return None
        return round(100.0 * qs.filter(is_mentioned=True).count() / total, 1)
    rates = [
        r for r in _audits_in(user, start, end).values_list("mention_rate", flat=True)
        if r is not None
    ]
    return round(sum(rates) / len(rates), 1) if rates else None


def _position(user, start, end, *, prompts=None) -> float | None:
    if start is None and end is None:
        return None
    if prompts:
        audit_ids = list(_audits_in(user, start, end).values_list("id", flat=True))
        if not audit_ids:
            return None
        ranks = list(
            _filtered_results(audit_ids, prompts)
            .filter(is_mentioned=True, mention_rank__isnull=False)
            .values_list("mention_rank", flat=True)
        )
        return round(sum(ranks) / len(ranks), 1) if ranks else None
    ranks = list(
        _audits_in(user, start, end)
        .filter(avg_mention_rank__gt=0)
        .values_list("avg_mention_rank", flat=True)
    )
    return round(sum(ranks) / len(ranks), 1) if ranks else None


def _sentiment(user, start, end, *, prompts=None) -> float | None:
    if start is None and end is None:
        return None
    audit_ids = list(_audits_in(user, start, end).values_list("id", flat=True))
    if not audit_ids:
        return None
    results = _filtered_results(audit_ids, prompts).filter(is_mentioned=True)
    total = results.count()
    if total == 0:
        return None
    pos = results.filter(sentiment=LLMRankingResult.SENTIMENT_POSITIVE).count()
    neg = results.filter(sentiment=LLMRankingResult.SENTIMENT_NEGATIVE).count()
    # 100 = all mentions positive, 50 = balanced/neutral, 0 = all negative.
    net = 50 + 50 * (pos - neg) / total
    return round(max(0.0, min(100.0, net)), 1)


# ── tile shaping ───────────────────────────────────────────────────────────

def _build_tile(*, label, subtext, higher_better, value_fmt, current, previous) -> dict:
    value = value_fmt(current)
    if current is None or previous is None or previous == 0:
        return {
            "label": label,
            "value": value,
            "change": "—",
            "direction": "up",
            "subtext": subtext,
            "trendNote": "No prior period to compare",
        }
    delta = current - previous
    if higher_better:
        direction = "up" if delta >= 0 else "down"
    else:
        direction = "up" if delta <= 0 else "down"
    pct = abs(delta) / abs(previous) * 100 if previous else 0.0
    return {
        "label": label,
        "value": value,
        "change": f"{pct:.1f}%",
        "direction": direction,
        "subtext": subtext,
        "trendNote": "Trending up" if direction == "up" else "Trending down",
    }


def _pct(v): return "—" if v is None else f"{v:.1f}%"
def _rank(v): return "—" if v is None else f"{v:.1f}"
def _score(v): return "—" if v is None else f"{v:.0f}"
