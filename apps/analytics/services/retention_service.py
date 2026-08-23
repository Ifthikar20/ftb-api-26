"""Cohort-based retention analysis."""
import logging
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from apps.analytics.models import PageEvent, Visitor
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
        from django.db.models import Avg, Count, DurationField, F, Q

        from apps.analytics.models import Session

        start, end = get_date_range(period)

        # ── Visitor counts: one scan, four numbers ──
        # These four differ only by date predicate, and every one of them is
        # a subset of first_seen <= end, so a filtered aggregate computes all
        # four in a single pass instead of four COUNTs over the same index.
        vc = Visitor.objects.filter(
            website_id=website_id,
            first_seen__lte=end,
        ).aggregate(
            total=Count("id"),
            new=Count("id", filter=Q(first_seen__range=(start, end))),
            returning=Count("id", filter=Q(
                first_seen__lt=start,
                last_seen__range=(start, end),
            )),
            multi=Count("id", filter=Q(
                first_seen__range=(start, end),
                visit_count__gt=1,
            )),
        )
        total_visitors = vc["total"]
        new_visitors = vc["new"]
        returning_total = vc["returning"] + vc["multi"]

        # ── Session metrics: one scan, four numbers ──
        # Postgres averages the interval directly, which retires the previous
        # `for s in ended_sessions[:200]` loop. That loop was not only 200
        # rows over the wire: it had no order_by, so it averaged 200
        # arbitrary sessions and reported the result as the period average.
        # Past 200 ended sessions in a window the figure quietly stopped
        # meaning what the dashboard label claims.
        sessions_in_period = Session.objects.filter(
            visitor__website_id=website_id,
            started_at__range=(start, end),
        )
        sm = sessions_in_period.aggregate(
            total=Count("id"),
            bounced=Count("id", filter=Q(page_count__lte=1)),
            avg_pages=Avg("page_count"),
            avg_duration=Avg(
                F("ended_at") - F("started_at"),
                filter=Q(ended_at__isnull=False),
                output_field=DurationField(),
            ),
        )
        total_sessions = sm["total"]
        bounce_rate = round(sm["bounced"] / max(total_sessions, 1) * 100, 1)
        avg_pages = sm["avg_pages"] or 0
        avg_duration = (
            round(sm["avg_duration"].total_seconds()) if sm["avg_duration"] else 0
        )

        # ── Engagement score (0-100) ──
        # Weighted: low bounce (40%), pages/session (30%), return rate (30%)
        bounce_score = max(0, (100 - bounce_rate)) * 0.4
        pages_score = min(avg_pages / 5, 1.0) * 30
        return_rate = returning_total / max(total_visitors, 1) * 100
        return_score = min(return_rate, 100) * 0.3
        engagement_score = round(bounce_score + pages_score + return_score)

        # ── Top returning visitors: annotate instead of one query each ──
        # This previously ran a separate Avg aggregate per returner, so the
        # ten-row list cost eleven queries. Visitor is unique_together on
        # (website, fingerprint_hash), so annotating per Visitor row returns
        # exactly what the per-visitor lookup returned - it just does it once.
        top_returners = (
            Visitor.objects.filter(
                website_id=website_id,
                visit_count__gt=1,
            )
            .annotate(avg_pages=Avg("sessions__page_count"))
            .order_by("-visit_count", "-last_seen")
            .values(
                "fingerprint_hash", "visit_count", "last_seen",
                "device_type", "geo_country", "browser", "avg_pages",
            )[:10]
        )

        returner_list = [
            {
                "hash": (v["fingerprint_hash"] or "")[:12],
                "visits": v["visit_count"],
                "last_seen": v["last_seen"].isoformat() if v["last_seen"] else None,
                "device": v["device_type"] or "",
                "country": v["geo_country"] or "",
                "browser": v["browser"] or "",
                "avg_pages": round(v["avg_pages"] or 0, 1),
            }
            for v in top_returners
        ]

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

