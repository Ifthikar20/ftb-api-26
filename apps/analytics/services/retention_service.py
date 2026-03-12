"""Cohort-based retention analysis."""
import logging
from datetime import timedelta
from collections import defaultdict

from django.db.models import Count, Min
from django.utils import timezone

from apps.analytics.models import Visitor, PageEvent
from core.utils.date_utils import get_date_range

logger = logging.getLogger("apps")


class RetentionService:
    @staticmethod
    def get_retention_matrix(*, website_id: str, num_weeks: int = 8) -> dict:
        """
        Build a cohort retention matrix.
        Groups visitors by the week they first appeared,
        then checks how many returned in subsequent weeks.
        """
        now = timezone.now()
        matrix_start = now - timedelta(weeks=num_weeks)

        # Get all visitors who first visited in our window
        visitors = Visitor.objects.filter(
            website_id=website_id,
            first_seen__gte=matrix_start,
        ).values("id", "first_seen")

        # Build cohorts — group visitors by week of first visit
        cohorts = defaultdict(set)  # week_num -> set of visitor_ids
        visitor_first_week = {}

        for v in visitors:
            week_num = (v["first_seen"].date() - matrix_start.date()).days // 7
            if 0 <= week_num < num_weeks:
                cohorts[week_num].add(v["id"])
                visitor_first_week[v["id"]] = week_num

        # Get all pageview events in the window grouped by visitor + week
        events = (
            PageEvent.objects.filter(
                website_id=website_id,
                event_type="pageview",
                timestamp__gte=matrix_start,
                visitor_id__in=list(visitor_first_week.keys()),
            )
            .values("visitor_id", "timestamp")
        )

        # Track which weeks each visitor was active
        visitor_active_weeks = defaultdict(set)
        for e in events:
            week_num = (e["timestamp"].date() - matrix_start.date()).days // 7
            visitor_active_weeks[e["visitor_id"]].add(week_num)

        # Build the retention matrix
        rows = []
        for cohort_week in range(num_weeks):
            cohort_visitors = cohorts.get(cohort_week, set())
            cohort_size = len(cohort_visitors)
            if cohort_size == 0:
                continue

            week_label = (matrix_start + timedelta(weeks=cohort_week)).strftime("%b %d")
            retention_row = {
                "cohort": week_label,
                "cohort_size": cohort_size,
                "weeks": [],
            }

            for offset in range(num_weeks - cohort_week):
                target_week = cohort_week + offset
                retained = sum(
                    1 for vid in cohort_visitors
                    if target_week in visitor_active_weeks.get(vid, set())
                )
                pct = round(retained / cohort_size * 100, 1) if cohort_size > 0 else 0
                retention_row["weeks"].append({
                    "week": offset,
                    "retained": retained,
                    "pct": pct,
                })

            rows.append(retention_row)

        return {
            "num_weeks": num_weeks,
            "rows": rows,
        }

    @staticmethod
    def get_retention_curve(*, website_id: str, num_weeks: int = 8) -> list:
        """Averaged retention curve across all cohorts."""
        matrix = RetentionService.get_retention_matrix(
            website_id=website_id, num_weeks=num_weeks
        )
        if not matrix["rows"]:
            return []

        # Average each week offset across all cohorts
        max_weeks = max(len(r["weeks"]) for r in matrix["rows"])
        curve = []
        for offset in range(max_weeks):
            pcts = [
                r["weeks"][offset]["pct"]
                for r in matrix["rows"]
                if offset < len(r["weeks"])
            ]
            avg = round(sum(pcts) / len(pcts), 1) if pcts else 0
            curve.append({"week": offset, "avg_retention_pct": avg})

        return curve

    @staticmethod
    def get_engagement_metrics(*, website_id: str, period: str = "30d") -> dict:
        """
        Compute engagement and retention metrics:
        - New vs returning visitors
        - Bounce rate
        - Avg pages per session
        - Avg session duration
        - Engagement score
        """
        from apps.analytics.models import Session
        from django.db.models import Avg, Sum, F

        start, end = get_date_range(period)

        # ── Visitor counts ──
        total_visitors = Visitor.objects.filter(
            website_id=website_id,
            first_seen__lte=end,
        ).count()

        new_visitors = Visitor.objects.filter(
            website_id=website_id,
            first_seen__range=(start, end),
        ).count()

        returning_visitors = Visitor.objects.filter(
            website_id=website_id,
            first_seen__lt=start,
            last_seen__range=(start, end),
        ).count()

        # Also count visitors who visited multiple times within the period
        multi_visit = Visitor.objects.filter(
            website_id=website_id,
            first_seen__range=(start, end),
            visit_count__gt=1,
        ).count()

        returning_total = returning_visitors + multi_visit

        # ── Session metrics ──
        sessions_in_period = Session.objects.filter(
            visitor__website_id=website_id,
            started_at__range=(start, end),
        )

        total_sessions = sessions_in_period.count()
        bounced_sessions = sessions_in_period.filter(page_count__lte=1).count()
        bounce_rate = round(bounced_sessions / max(total_sessions, 1) * 100, 1)

        avg_pages = sessions_in_period.aggregate(
            avg=Avg("page_count")
        )["avg"] or 0

        # Avg duration (from sessions that have ended)
        ended_sessions = sessions_in_period.filter(ended_at__isnull=False)
        durations = []
        for s in ended_sessions[:200]:
            if s.ended_at and s.started_at:
                durations.append((s.ended_at - s.started_at).total_seconds())
        avg_duration = round(sum(durations) / max(len(durations), 1))

        # ── Engagement score (0-100) ──
        # Weighted: low bounce (40%), pages/session (30%), return rate (30%)
        bounce_score = max(0, (100 - bounce_rate)) * 0.4
        pages_score = min(avg_pages / 5, 1.0) * 30
        return_rate = returning_total / max(total_visitors, 1) * 100
        return_score = min(return_rate, 100) * 0.3
        engagement_score = round(bounce_score + pages_score + return_score)

        # ── Top returning visitors ──
        top_returners = list(
            Visitor.objects.filter(
                website_id=website_id,
                visit_count__gt=1,
            )
            .order_by("-visit_count", "-last_seen")[:10]
            .values(
                "fingerprint_hash", "visit_count", "last_seen",
                "device_type", "geo_country", "browser", "os",
            )
        )

        returner_list = []
        for v in top_returners:
            # Get avg pages per visit for this visitor
            visitor_sessions = Session.objects.filter(
                visitor__fingerprint_hash=v["fingerprint_hash"],
                visitor__website_id=website_id,
            )
            v_avg_pages = visitor_sessions.aggregate(avg=Avg("page_count"))["avg"] or 0
            returner_list.append({
                "hash": (v["fingerprint_hash"] or "")[:12],
                "visits": v["visit_count"],
                "last_seen": v["last_seen"].isoformat() if v["last_seen"] else None,
                "device": v["device_type"] or "",
                "country": v["geo_country"] or "",
                "browser": v["browser"] or "",
                "avg_pages": round(v_avg_pages, 1),
            })

        return {
            "total_visitors": total_visitors,
            "new_visitors": new_visitors,
            "returning_visitors": returning_total,
            "new_pct": round(new_visitors / max(total_visitors, 1) * 100, 1),
            "returning_pct": round(returning_total / max(total_visitors, 1) * 100, 1),
            "total_sessions": total_sessions,
            "bounce_rate": bounce_rate,
            "avg_pages_per_session": round(avg_pages, 1),
            "avg_session_duration_secs": avg_duration,
            "engagement_score": engagement_score,
            "top_returners": returner_list,
        }

