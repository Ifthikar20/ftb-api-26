from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.analytics.models import PageEvent, Session, Visitor
from core.utils.date_utils import get_date_range


class AnalyticsService:
    @staticmethod
    def get_overview(*, website_id: str, period: str = "30d", **kwargs) -> dict:
        """Return KPI overview for the analytics dashboard."""
        start, end = get_date_range(period, **kwargs)

        visitors_qs = Visitor.objects.filter(website_id=website_id, last_seen__range=(start, end))
        events_qs = PageEvent.objects.filter(website_id=website_id, timestamp__range=(start, end))

        total_visitors = visitors_qs.count()
        total_pageviews = events_qs.filter(event_type="pageview").count()
        hot_leads = visitors_qs.filter(lead_score__gte=70).count()

        # Previous period for comparison
        duration = end - start
        prev_start = start - duration
        prev_visitors = Visitor.objects.filter(
            website_id=website_id, last_seen__range=(prev_start, start)
        ).count()

        growth_pct = (
            ((total_visitors - prev_visitors) / prev_visitors * 100) if prev_visitors > 0 else 0
        )

        return {
            "period": period,
            "total_visitors": total_visitors,
            "total_pageviews": total_pageviews,
            "hot_leads": hot_leads,
            "visitor_growth_pct": round(growth_pct, 1),
        }

    @staticmethod
    def get_top_pages(*, website_id: str, period: str = "30d", limit: int = 10) -> list:
        """Return top pages by view count."""
        start, end = get_date_range(period)
        return list(
            PageEvent.objects.filter(
                website_id=website_id,
                event_type="pageview",
                timestamp__range=(start, end),
            )
            .values("url")
            .annotate(views=Count("id"))
            .order_by("-views")[:limit]
        )

    @staticmethod
    def get_traffic_sources(*, website_id: str, period: str = "30d") -> list:
        """Return traffic source breakdown."""
        start, end = get_date_range(period)
        raw = list(
            Session.objects.filter(
                visitor__website_id=website_id,
                started_at__range=(start, end),
            )
            .values("source", "medium")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        # Normalize sources: localhost, empty, None → 'Direct'
        IGNORE_SOURCES = {'localhost', 'localhost:5173', 'localhost:8000', '127.0.0.1', ''}
        merged = {}
        for r in raw:
            source = (r.get("source") or "").strip().lower()
            if source in IGNORE_SOURCES or not source:
                source = "Direct"
            else:
                # Capitalize nicely
                source = source.replace("www.", "").split("/")[0]
                source = source.title() if "." not in source else source
            medium = r.get("medium") or "none"
            key = f"{source}|{medium}"
            if key in merged:
                merged[key]["count"] += r["count"]
            else:
                merged[key] = {"source": source, "medium": medium, "count": r["count"]}
        return sorted(merged.values(), key=lambda x: -x["count"])

    @staticmethod
    def get_realtime_snapshot(*, website_id: str) -> dict:
        """Return current live visitor count (last 5 minutes)."""
        cutoff = timezone.now() - timedelta(minutes=5)
        active_count = Visitor.objects.filter(
            website_id=website_id, last_seen__gte=cutoff
        ).count()
        return {"active_visitors": active_count, "as_of": timezone.now().isoformat()}

    @staticmethod
    def get_ai_traffic_summary(*, website_id: str, period: str = "30d") -> dict:
        """Return AI-sourced traffic breakdown (sessions from AI assistants)."""
        start, end = get_date_range(period)

        all_sessions = Session.objects.filter(
            visitor__website_id=website_id,
            started_at__range=(start, end),
        ).count()

        ai_sessions = list(
            Session.objects.filter(
                visitor__website_id=website_id,
                started_at__range=(start, end),
                medium="ai",
            )
            .values("source")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        total_ai = sum(r["count"] for r in ai_sessions)
        ai_pct = round(total_ai / all_sessions * 100, 1) if all_sessions else 0.0

        # Provider display names
        provider_labels = {
            "chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini",
            "perplexity": "Perplexity", "copilot": "Copilot",
            "meta-ai": "Meta AI", "poe": "Poe", "you": "You.com",
        }

        providers = [
            {
                "source": r["source"],
                "label": provider_labels.get(r["source"], r["source"].title()),
                "sessions": r["count"],
            }
            for r in ai_sessions
        ]

        return {
            "total_sessions": all_sessions,
            "ai_sessions": total_ai,
            "ai_percentage": ai_pct,
            "providers": providers,
        }
