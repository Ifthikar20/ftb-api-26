"""Source-influence rollup service.

Aggregates Citation rows into SourceInfluenceSnapshot rows on a daily
schedule. Each snapshot is keyed by (provider, industry, website,
period_start, period_end) — website may be NULL for global rollups.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import date, timedelta
from typing import Iterable

from django.db.models import Count
from django.utils import timezone

from apps.citations.models import Citation, SourceInfluenceSnapshot

logger = logging.getLogger("apps")


def _build_breakdown(rows: Iterable[Citation]) -> tuple[dict, list, int]:
    """Return (breakdown, top_domains, total)."""
    cls_counter: Counter = Counter()
    domain_counter: Counter = Counter()
    total = 0
    for row in rows:
        cls_counter[row.source_class] += 1
        if row.apex_domain:
            domain_counter[row.apex_domain] += 1
        total += 1

    breakdown: dict = {}
    if total:
        for cls, count in cls_counter.items():
            breakdown[cls] = {
                "count": count,
                "share": round(count / total, 4),
            }

    top_domains = [
        {"apex_domain": d, "count": c}
        for d, c in domain_counter.most_common(20)
    ]
    return breakdown, top_domains, total


def compute_for_website(website, *, period_days: int = 30, end: date | None = None) -> int:
    """Build per-provider snapshots for ``website`` over the trailing window.

    Returns the number of snapshot rows upserted.
    """
    end = end or timezone.now().date()
    start = end - timedelta(days=period_days)

    qs = Citation.objects.filter(
        audit__website=website,
        created_at__date__gte=start,
        created_at__date__lte=end,
    ).only("source_class", "apex_domain", "audit_id")

    # Group by provider via the parent audit's results. We re-query per
    # provider to keep memory bounded when websites accumulate citations.
    from apps.llm_ranking.models import LLMRankingResult

    providers = list(
        LLMRankingResult.objects.filter(
            audit__website=website,
            created_at__date__gte=start,
        ).values_list("provider", flat=True).distinct()
    )

    upserts = 0
    for provider in providers:
        rows = list(
            Citation.objects.filter(
                audit__website=website,
                created_at__date__gte=start,
                created_at__date__lte=end,
                result__provider=provider,
            ).only("source_class", "apex_domain")
        )
        breakdown, top_domains, total = _build_breakdown(rows)
        SourceInfluenceSnapshot.objects.update_or_create(
            provider=provider, industry=None, website=website,
            period_start=start, period_end=end,
            defaults={
                "total_citations": total,
                "breakdown": breakdown,
                "top_domains": top_domains,
            },
        )
        upserts += 1
    return upserts


def compute_global(*, period_days: int = 30, end: date | None = None) -> int:
    """Build global per-provider/industry snapshots (website NULL).

    Industries are pulled from prompt_library when present. Falls back to
    a single industry-less rollup per provider.
    """
    end = end or timezone.now().date()
    start = end - timedelta(days=period_days)

    from apps.llm_ranking.models import LLMRankingResult

    providers = list(
        LLMRankingResult.objects.filter(created_at__date__gte=start)
        .values_list("provider", flat=True).distinct()
    )

    upserts = 0
    for provider in providers:
        rows = list(
            Citation.objects.filter(
                created_at__date__gte=start,
                created_at__date__lte=end,
                result__provider=provider,
            ).only("source_class", "apex_domain")
        )
        breakdown, top_domains, total = _build_breakdown(rows)
        SourceInfluenceSnapshot.objects.update_or_create(
            provider=provider, industry=None, website=None,
            period_start=start, period_end=end,
            defaults={
                "total_citations": total,
                "breakdown": breakdown,
                "top_domains": top_domains,
            },
        )
        upserts += 1
    return upserts


def compute_audit_breakdown(audit) -> dict:
    """Live (non-persisted) breakdown for one audit, grouped by provider."""
    citations = (
        Citation.objects.filter(audit=audit)
        .select_related("result")
        .only("source_class", "apex_domain", "result__provider")
    )
    by_provider: dict[str, list] = {}
    for c in citations:
        by_provider.setdefault(c.result.provider, []).append(c)

    out = {"providers": {}, "total_citations": 0, "unique_domains": 0}
    seen_domains: set[str] = set()
    for provider, rows in by_provider.items():
        breakdown, top_domains, total = _build_breakdown(rows)
        out["providers"][provider] = {
            "breakdown": breakdown,
            "top_domains": top_domains,
            "total_citations": total,
        }
        out["total_citations"] += total
        seen_domains.update(r.apex_domain for r in rows if r.apex_domain)
    out["unique_domains"] = len(seen_domains)
    return out
