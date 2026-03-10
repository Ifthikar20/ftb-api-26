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
