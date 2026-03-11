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

    @staticmethod
    def get_visitor_journeys(*, website_id: str, period: str = "30d", limit: int = 20) -> list:
        """
        Return per-visitor session journeys: the full sequence of pages
        each visitor viewed, grouped by session.
        """
        start, end = get_date_range(period)
        from apps.analytics.models import Session

        sessions = (
            Session.objects.filter(
                visitor__website_id=website_id,
                started_at__range=(start, end),
            )
            .select_related("visitor")
            .order_by("-started_at")[:limit * 2]  # fetch more to filter empties
        )

        journeys = []
        for sess in sessions:
            # Get all pageview events in this session
            events = list(
                PageEvent.objects.filter(
                    session=sess, event_type="pageview"
                )
                .order_by("timestamp")
                .values_list("url", flat=True)
            )
            if not events:
                continue

            # Normalize URLs to paths
            pages = []
            for url in events:
                try:
                    from urllib.parse import urlparse
                    path = urlparse(url).path or "/"
                except Exception:
                    path = url
                # Deduplicate consecutive same page
                if not pages or pages[-1] != path:
                    pages.append(path)

            duration_secs = 0
            if sess.ended_at and sess.started_at:
                duration_secs = int((sess.ended_at - sess.started_at).total_seconds())

            v = sess.visitor
            journeys.append({
                "visitor_hash": (v.fingerprint_hash or "")[:12],
                "company": v.company_name or "",
                "device": v.device_type or "",
                "country": v.geo_country or "",
                "pages": pages,
                "page_count": len(pages),
                "duration_secs": duration_secs,
                "source": sess.source or "direct",
                "started_at": sess.started_at.isoformat() if sess.started_at else None,
            })

            if len(journeys) >= limit:
                break

        return journeys
