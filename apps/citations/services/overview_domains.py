"""Top-domain and domain-type cards for the Overview dashboard.

Owned by the citations app because the data root is ``Citation`` and the
type buckets come from :func:`domain_type_for` — llm_ranking's overview
assembler calls this at its composition seam rather than importing
Citation itself, so the app dependency stays one-way
(citations -> llm_ranking).
"""
from __future__ import annotations

from collections import defaultdict

from apps.citations.models import Citation
from apps.citations.services.url_analytics import domain_type_for

MAX_DOMAINS = 8

# Matching the frontend legend in DomainTypesCard.
DOMAIN_TYPE_COLORS = {
    "Corporate": "var(--chart-1)",
    "UGC": "var(--chart-2)",
    "Editorial": "var(--chart-3)",
    "Reference": "var(--chart-4)",
    "Your site": "var(--chart-2)",
    "Competitor": "var(--chart-3)",
}


def build_domain_cards(
    audit_ids, *, providers=None, tags=None, topics=None,
) -> tuple[list[dict], dict | None]:
    """Return (top-domain rows, domain-type split) for the given audits.

    Citations filter through their result FK so the Top Sources cards
    agree with the rest of a filtered page. This is the one spot that
    cannot reuse apply_result_filters (different model root) — keep the
    predicates in lockstep with it.
    """
    qs = Citation.objects.filter(audit_id__in=audit_ids)
    if providers:
        qs = qs.filter(result__provider__in=providers)
    if topics:
        qs = qs.filter(result__source_prompt__industry__name__in=topics)
    if tags:
        from django.db.models import F, Q

        tag_q = Q()
        for tag in tags:
            tag_q |= Q(result__source_prompt__brand_prompts__tags__contains=[tag])
        qs = qs.filter(
            tag_q,
            result__source_prompt__brand_prompts__website_id=F("audit__website_id"),
        )
    if tags or topics:
        qs = qs.distinct()
    citations = list(
        qs.values_list(
            "apex_domain", "domain", "source_class", "reference_count",
        ),
    )
    if not citations:
        return [], None

    total = len(citations)
    retrieved: dict[str, int] = defaultdict(int)
    cited: dict[str, int] = defaultdict(int)
    types: dict[str, str] = {}
    type_counts: dict[str, int] = defaultdict(int)

    for apex, domain, source_class, ref_count in citations:
        key = apex or domain
        if not key:
            continue
        retrieved[key] += 1
        if (ref_count or 0) > 0:
            cited[key] += 1
        bucket = domain_type_for(source_class)
        types[key] = bucket
        type_counts[bucket] += 1

    if not retrieved:
        return [], None

    rows = [
        {
            "domain": key,
            "retrieved": _pct(count, total),
            # Cited share, matching the citation_rate definition used by
            # the Sources dashboard: retrievals with an explicit reference
            # / all retrievals, bounded 0-1.
            "citation": round(cited[key] / count, 2) if count else 0.0,
            "type": types.get(key, "Reference"),
        }
        for key, count in sorted(retrieved.items(), key=lambda kv: -kv[1])[:MAX_DOMAINS]
    ]

    domain_types = {
        "total": _humanize(total),
        "types": [
            {
                "label": label,
                "pct": _pct(count, total),
                "color": DOMAIN_TYPE_COLORS.get(label, "var(--chart-3)"),
            }
            for label, count in sorted(type_counts.items(), key=lambda kv: -kv[1])
        ],
    }
    return rows, domain_types


def _pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0


def _humanize(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)
