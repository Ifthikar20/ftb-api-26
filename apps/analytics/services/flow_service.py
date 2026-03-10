"""User flow / path analysis."""
import logging
from collections import defaultdict, Counter

from django.db.models import Count
from apps.analytics.models import PageEvent
from core.utils.date_utils import get_date_range

logger = logging.getLogger("apps")


class FlowService:
    @staticmethod
    def get_user_flows(*, website_id: str, period: str = "30d", depth: int = 4) -> dict:
        """
        Aggregate page-to-page transitions for Sankey / flow visualization.
        Returns nodes (pages) and links (transitions with counts).
        """
        start, end = get_date_range(period)

        # Get pageview events ordered by visitor then timestamp
        events = (
            PageEvent.objects.filter(
                website_id=website_id,
                event_type="pageview",
                timestamp__range=(start, end),
            )
            .order_by("visitor_id", "timestamp")
            .values_list("visitor_id", "url")
        )

        # Build transitions
        transitions = Counter()
        current_visitor = None
        visitor_path = []

        for visitor_id, url in events:
            # Normalize URL to path only
            try:
                from urllib.parse import urlparse
                path = urlparse(url).path or "/"
            except Exception:
                path = url

            if visitor_id != current_visitor:
                # New visitor — process previous path
                FlowService._count_transitions(visitor_path, transitions, depth)
                current_visitor = visitor_id
                visitor_path = [path]
            else:
                if not visitor_path or visitor_path[-1] != path:
                    visitor_path.append(path)

        # Process last visitor
        FlowService._count_transitions(visitor_path, transitions, depth)

        # Build nodes and links
        all_pages = set()
        links = []
        for (source, target), count in transitions.most_common(50):
            all_pages.add(source)
            all_pages.add(target)
            links.append({"source": source, "target": target, "value": count})

        nodes = [{"id": p, "label": p} for p in sorted(all_pages)]

        return {
            "nodes": nodes,
            "links": links,
            "total_paths": sum(transitions.values()),
        }

    @staticmethod
    def _count_transitions(path, transitions, depth):
        """Count transitions in a visitor path up to depth steps."""
        for i in range(min(len(path) - 1, depth)):
            transitions[(path[i], path[i + 1])] += 1

    @staticmethod
    def get_entry_pages(*, website_id: str, period: str = "30d", limit: int = 10) -> list:
        """Top pages where visitors start their session."""
        start, end = get_date_range(period)
        from apps.analytics.models import Session

        qs = (
            Session.objects.filter(
                visitor__website_id=website_id,
                started_at__range=(start, end),
            )
            .exclude(entry_page="")
            .values("entry_page")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        total = sum(r["count"] for r in qs) or 1
        return [
            {
                "page": r["entry_page"],
                "count": r["count"],
                "pct": round(r["count"] / total * 100, 1),
            }
            for r in qs
        ]

    @staticmethod
    def get_exit_pages(*, website_id: str, period: str = "30d", limit: int = 10) -> list:
        """Top pages where visitors leave."""
        start, end = get_date_range(period)
        from apps.analytics.models import Session

        qs = (
            Session.objects.filter(
                visitor__website_id=website_id,
                started_at__range=(start, end),
            )
            .exclude(exit_page="")
            .values("exit_page")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        total = sum(r["count"] for r in qs) or 1
        return [
            {
                "page": r["exit_page"],
                "count": r["count"],
                "pct": round(r["count"] / total * 100, 1),
            }
            for r in qs
        ]
