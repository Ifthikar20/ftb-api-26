"""Source-influence rollup service.

Aggregates Citation rows into SourceInfluenceSnapshot rows on a daily
schedule. Each snapshot is keyed by (provider, industry, website,
period_start, period_end) — website may be NULL for global rollups.
"""
from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable
from datetime import date, timedelta

from django.utils import timezone

from apps.citations.models import Citation, SourceInfluenceSnapshot

logger = logging.getLogger("apps")


def _build_breakdown(rows: Iterable[Citation]) -> tuple[dict, list, int]:
    """Return (breakdown, top_domains, total).

    ``top_domains`` entries carry ``source_class``, ``is_target`` and
    ``is_competitor`` flags resolved from the most common values seen on
    the citation rows for that apex_domain.
    """
    cls_counter: Counter = Counter()
    domain_counter: Counter = Counter()
    # Per-domain attribute aggregators.
    domain_class_counter: dict[str, Counter] = {}
    domain_target: dict[str, int] = {}
    domain_competitor: dict[str, int] = {}
    total = 0
    for row in rows:
        cls_counter[row.source_class] += 1
        if row.apex_domain:
            domain_counter[row.apex_domain] += 1
            domain_class_counter.setdefault(row.apex_domain, Counter())[
                row.source_class
            ] += 1
            if getattr(row, "is_target", False):
                domain_target[row.apex_domain] = domain_target.get(row.apex_domain, 0) + 1
            if getattr(row, "is_competitor", False):
                domain_competitor[row.apex_domain] = (
                    domain_competitor.get(row.apex_domain, 0) + 1
                )
        total += 1

    breakdown: dict = {}
    if total:
        for cls, count in cls_counter.items():
            breakdown[cls] = {
                "count": count,
                "share": round(count / total, 4),
            }

    top_domains = []
    for d, c in domain_counter.most_common(20):
        cls_for_domain = "other"
        if d in domain_class_counter and domain_class_counter[d]:
            cls_for_domain = domain_class_counter[d].most_common(1)[0][0]
        top_domains.append({
            "apex_domain": d,
            "count": c,
            "share": round(c / total, 4) if total else 0,
            "source_class": cls_for_domain,
            "is_target": domain_target.get(d, 0) > 0,
            "is_competitor": domain_competitor.get(d, 0) > 0,
        })
    return breakdown, top_domains, total


def compute_for_website(website, *, period_days: int = 30, end: date | None = None) -> int:
    """Build per-provider snapshots for ``website`` over the trailing window.

    Returns the number of snapshot rows upserted.
    """
    end = end or timezone.now().date()
    start = end - timedelta(days=period_days)

    Citation.objects.filter(
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
            ).only("source_class", "apex_domain", "is_target", "is_competitor")
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
            ).only("source_class", "apex_domain", "is_target", "is_competitor")
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
        .only("source_class", "apex_domain", "is_target", "is_competitor", "result__provider")
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
