"""Pre-aggregated daily statistics for fast chart rendering."""
import logging
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Avg, Q, F
from django.utils import timezone

from apps.analytics.models import Visitor, PageEvent, Session
from core.utils.date_utils import get_date_range

logger = logging.getLogger("apps")


class DailyStatsService:
    @staticmethod
    def get_chart_data(*, website_id: str, period: str = "30d") -> list:
        """Return day-by-day visitor + pageview counts for the area chart."""
        start, end = get_date_range(period)

        # Pageviews per day
        pv_qs = (
            PageEvent.objects.filter(
                website_id=website_id,
                event_type="pageview",
                timestamp__range=(start, end),
            )
            .extra(select={"day": "DATE(timestamp)"})
            .values("day")
            .annotate(pageviews=Count("id"))
            .order_by("day")
        )
        pv_map = {str(r["day"]): r["pageviews"] for r in pv_qs}

        # Unique visitors per day (by distinct fingerprint)
        vis_qs = (
            PageEvent.objects.filter(
                website_id=website_id,
                event_type="pageview",
                timestamp__range=(start, end),
            )
            .extra(select={"day": "DATE(timestamp)"})
            .values("day")
            .annotate(visitors=Count("visitor", distinct=True))
            .order_by("day")
        )
        vis_map = {str(r["day"]): r["visitors"] for r in vis_qs}

        # Sessions per day
        sess_qs = (
            Session.objects.filter(
                visitor__website_id=website_id,
                started_at__range=(start, end),
            )
            .extra(select={"day": "DATE(started_at)"})
            .values("day")
            .annotate(sessions=Count("id"))
            .order_by("day")
        )
        sess_map = {str(r["day"]): r["sessions"] for r in sess_qs}

        # Build day-by-day series
        days = []
        current = start.date() if hasattr(start, "date") else start
        end_date = end.date() if hasattr(end, "date") else end
        while current <= end_date:
            key = str(current)
            days.append({
                "date": key,
                "label": current.strftime("%b %d"),
                "visitors": vis_map.get(key, 0),
                "pageviews": pv_map.get(key, 0),
                "sessions": sess_map.get(key, 0),
            })
            current += timedelta(days=1)

        return days

    @staticmethod
    def get_device_breakdown(*, website_id: str, period: str = "30d") -> dict:
        """Return device type, browser, and OS distribution."""
        start, end = get_date_range(period)
        base_qs = Visitor.objects.filter(
            website_id=website_id, last_seen__range=(start, end)
        )

        # Device type breakdown
        device_qs = (
            base_qs.values("device_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        device_total = sum(r["count"] for r in device_qs) or 1
        colors = {
            "desktop": "var(--brand-accent)",
            "mobile": "var(--text-primary)",
            "tablet": "var(--text-muted)",
        }
        devices = [
            {
                "name": r["device_type"].capitalize() if r["device_type"] else "Unknown",
                "count": r["count"],
                "pct": round(r["count"] / device_total * 100, 1),
                "color": colors.get(r["device_type"], "var(--text-muted)"),
            }
            for r in device_qs
        ]

        # Browser breakdown
        browser_qs = (
            base_qs.exclude(browser="")
            .values("browser")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )
        browser_total = sum(r["count"] for r in browser_qs) or 1
        browsers = [
            {
                "name": r["browser"] or "Unknown",
                "count": r["count"],
                "pct": round(r["count"] / browser_total * 100, 1),
            }
            for r in browser_qs
        ]

        # OS breakdown
        os_qs = (
            base_qs.exclude(os="")
            .values("os")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )
        os_total = sum(r["count"] for r in os_qs) or 1
        operating_systems = [
            {
                "name": r["os"] or "Unknown",
                "count": r["count"],
                "pct": round(r["count"] / os_total * 100, 1),
            }
            for r in os_qs
        ]

        return {
            "devices": devices,
            "browsers": browsers,
            "operating_systems": operating_systems,
        }

    @staticmethod
    def get_country_breakdown(*, website_id: str, period: str = "30d", limit: int = 10) -> list:
        """Return visitors by country."""
        start, end = get_date_range(period)
        qs = (
            Visitor.objects.filter(
                website_id=website_id, last_seen__range=(start, end)
            )
            .exclude(geo_country="")
            .values("geo_country")
            .annotate(visitors=Count("id"))
            .order_by("-visitors")[:limit]
        )
        total = sum(r["visitors"] for r in qs) or 1
        return [
            {
                "name": r["geo_country"],
                "visitors": r["visitors"],
                "pct": round(r["visitors"] / total * 100, 1),
            }
            for r in qs
        ]

    @staticmethod
    def get_bounce_rate(*, website_id: str, period: str = "30d") -> float:
        """Bounce rate = sessions with only 1 pageview / total sessions."""
        start, end = get_date_range(period)
        total = Session.objects.filter(
            visitor__website_id=website_id, started_at__range=(start, end)
        ).count()
        if not total:
            return 0.0
        bounced = Session.objects.filter(
            visitor__website_id=website_id,
            started_at__range=(start, end),
            page_count__lte=1,
        ).count()
        return round(bounced / total * 100, 1)

    @staticmethod
    def get_avg_session_duration(*, website_id: str, period: str = "30d") -> str:
        """Average session duration in human-readable format."""
        start, end = get_date_range(period)
        sessions = Session.objects.filter(
            visitor__website_id=website_id,
            started_at__range=(start, end),
            ended_at__isnull=False,
        )
        result = sessions.aggregate(
            avg_duration=Avg(F("ended_at") - F("started_at"))
        )
        avg = result.get("avg_duration")
        if not avg:
            return "0:00"
        total_seconds = int(avg.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
