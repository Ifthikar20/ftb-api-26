"""Per-agent data gatherers.

Each gatherer reads existing domain data for a (user, website) and returns a
small, JSON-serialisable dict that the runner feeds to the LLM. Gatherers do
NO new analytics — they summarise what other apps already produce. They must
tolerate empty data (a freshly hired agent on a new website).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")


def visibility_analyst(user, website) -> dict:
    """Latest LLM-ranking audit results + trend vs the previous run."""
    from apps.llm_ranking.models import LLMRankingAudit

    audits = list(
        LLMRankingAudit.objects.filter(
            website=website, status=LLMRankingAudit.STATUS_COMPLETED
        )
        .order_by("-created_at")
        .values(
            "id", "overall_score", "mention_rate", "avg_mention_rank",
            "providers_queried", "created_at",
        )[:2]
    )
    latest = audits[0] if audits else None
    prev = audits[1] if len(audits) > 1 else None
    out = {"has_data": bool(latest)}
    if latest:
        out["current"] = {
            "audit_id": str(latest["id"]),
            "overall_score": latest["overall_score"],
            "mention_rate": round(latest["mention_rate"], 3),
            "avg_mention_rank": round(latest["avg_mention_rank"], 2),
            "providers": latest["providers_queried"],
            "as_of": latest["created_at"].isoformat(),
        }
    if prev:
        out["score_delta"] = latest["overall_score"] - prev["overall_score"]
        out["mention_rate_delta"] = round(
            latest["mention_rate"] - prev["mention_rate"], 3
        )
    return out


def citation_hunter(user, website) -> dict:
    """Most recent source-influence snapshots: who AI cites about you."""
    from apps.citations.models import SourceInfluenceSnapshot

    snaps = list(
        SourceInfluenceSnapshot.objects.filter(website=website)
        .order_by("-period_end")
        .values("provider", "total_citations", "top_domains", "breakdown", "period_end")[:6]
    )
    return {
        "has_data": bool(snaps),
        "snapshots": [
            {
                "provider": s["provider"],
                "total_citations": s["total_citations"],
                "top_domains": (s["top_domains"] or [])[:8],
                "breakdown": s["breakdown"],
                "as_of": s["period_end"].isoformat() if s["period_end"] else None,
            }
            for s in snaps
        ],
    }


def content_strategist(user, website) -> dict:
    """Top open content briefs (visibility/accuracy gaps to close)."""
    from apps.content_studio.models import ContentBrief

    briefs = list(
        ContentBrief.objects.filter(website=website, status="open")
        .order_by("-impact_score")
        .values("id", "gap_type", "target_format", "headline", "impact_score")[:8]
    )
    return {
        "has_data": bool(briefs),
        "briefs": [
            {
                "brief_id": str(b["id"]),
                "gap_type": b["gap_type"],
                "format": b["target_format"],
                "headline": b["headline"],
                "impact_score": round(b["impact_score"], 2),
            }
            for b in briefs
        ],
    }


def lead_scout(user, website) -> dict:
    """Highest-scoring recent visitors/leads."""
    from apps.analytics.models import Visitor

    visitors = list(
        Visitor.objects.filter(website=website)
        .order_by("-lead_score", "-last_seen")
        .values(
            "company_name", "geo_country", "geo_city",
            "lead_score", "visit_count", "last_seen",
        )[:10]
    )
    return {
        "has_data": bool(visitors),
        "leads": [
            {
                "company": v["company_name"] or "Unknown",
                "geo": ", ".join(x for x in [v["geo_city"], v["geo_country"]] if x),
                "lead_score": v["lead_score"],
                "visits": v["visit_count"],
                "last_seen": v["last_seen"].isoformat() if v["last_seen"] else None,
            }
            for v in visitors
        ],
    }


def brand_watchdog(user, website) -> dict:
    """Open safety alerts: inaccurate/risky AI mentions of the brand."""
    from apps.brand_vault.models import SafetyAlert

    alerts = list(
        SafetyAlert.objects.filter(
            website=website, status=SafetyAlert.STATUS_OPEN
        )
        .order_by("-created_at")
        .values("id", "issue", "severity", "model", "prompt_text", "snippet")[:10]
    )
    return {
        "has_data": bool(alerts),
        "alerts": [
            {
                "alert_id": str(a["id"]),
                "issue": a["issue"],
                "severity": a["severity"],
                "model": a["model"],
                "prompt": a["prompt_text"],
                "snippet": (a["snippet"] or "")[:280],
            }
            for a in alerts
        ],
    }
