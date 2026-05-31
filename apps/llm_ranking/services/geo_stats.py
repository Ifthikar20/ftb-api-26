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

from django.utils import timezone

from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult

PERIOD_DAYS = 30


def build_kpis_for_user(user) -> list[dict] | None:
    """Return the Visibility / Position / Sentiment tiles, or None if no data."""
    has_any = LLMRankingAudit.objects.filter(
        created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
    ).exists()
    if not has_any:
        return None

    now = timezone.now()
    current = (now - timedelta(days=PERIOD_DAYS), now)
    previous = (
        now - timedelta(days=PERIOD_DAYS * 2),
        now - timedelta(days=PERIOD_DAYS),
    )

    return [
        _build_tile(
            label="Visibility",
            subtext="Share of AI answers you appear in",
            higher_better=True,
            value_fmt=_pct,
            current=_visibility(user, *current),
            previous=_visibility(user, *previous),
        ),
        _build_tile(
            label="Position",
            subtext="Average rank when mentioned (lower is better)",
            higher_better=False,
            value_fmt=_rank,
            current=_position(user, *current),
            previous=_position(user, *previous),
        ),
        _build_tile(
            label="Sentiment",
            subtext="Net sentiment score (0-100)",
            higher_better=True,
            value_fmt=_score,
            current=_sentiment(user, *current),
            previous=_sentiment(user, *previous),
        ),
    ]


# ── metric calculators ─────────────────────────────────────────────────────

def _audits_in(user, start, end):
    return LLMRankingAudit.objects.filter(
        created_by=user,
        status=LLMRankingAudit.STATUS_COMPLETED,
        completed_at__gte=start,
        completed_at__lt=end,
    )


def _visibility(user, start, end) -> float | None:
    rates = [
        r for r in _audits_in(user, start, end).values_list("mention_rate", flat=True)
        if r is not None
    ]
    return round(sum(rates) / len(rates), 1) if rates else None


def _position(user, start, end) -> float | None:
    ranks = list(
        _audits_in(user, start, end)
        .filter(avg_mention_rank__gt=0)
        .values_list("avg_mention_rank", flat=True)
    )
    return round(sum(ranks) / len(ranks), 1) if ranks else None


def _sentiment(user, start, end) -> float | None:
    audit_ids = list(_audits_in(user, start, end).values_list("id", flat=True))
    if not audit_ids:
        return None
    results = LLMRankingResult.objects.filter(
        audit_id__in=audit_ids, query_succeeded=True, is_mentioned=True,
    )
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
