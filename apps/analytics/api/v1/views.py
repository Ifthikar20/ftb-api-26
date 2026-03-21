from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, FormParser
from rest_framework import status
import json

from apps.analytics.services.event_ingestion_service import EventIngestionService
from apps.analytics.services.analytics_service import AnalyticsService
from apps.websites.services.website_service import WebsiteService
from core.interceptors.throttling import PixelIngestThrottle


class PlainTextJSONParser:
    """Parse JSON sent as text/plain (navigator.sendBeacon default)."""
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return json.loads(stream.read())
        except (json.JSONDecodeError, Exception):
            return {}


class EventIngestView(APIView):
    """Public pixel ingestion endpoint."""
    permission_classes = [AllowAny]
    throttle_classes = [PixelIngestThrottle]
    parser_classes = [JSONParser, PlainTextJSONParser, FormParser]

    def post(self, request):
        pixel_key = request.data.get("pixel_key")
        if not pixel_key:
            return Response({"error": "pixel_key required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            EventIngestionService.ingest_event(
                pixel_key=pixel_key, event_data=request.data, request=request
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"ok": True}, status=status.HTTP_202_ACCEPTED)


class BatchEventIngestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PixelIngestThrottle]
    parser_classes = [JSONParser, PlainTextJSONParser, FormParser]

    def post(self, request):
        pixel_key = request.data.get("pixel_key")
        events = request.data.get("events", [])
        if not pixel_key or not events:
            return Response({"error": "pixel_key and events required"}, status=status.HTTP_400_BAD_REQUEST)

        results = EventIngestionService.ingest_batch(pixel_key=pixel_key, events=events, request=request)
        return Response({"ingested": len(results)}, status=status.HTTP_202_ACCEPTED)


class AnalyticsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_overview(website_id=website_id, period=period)
        return Response(data)


class TopPagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_top_pages(website_id=website_id, period=period)
        return Response(data)


class TrafficSourcesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_traffic_sources(website_id=website_id, period=period)
        return Response(data)


class RealtimeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        data = AnalyticsService.get_realtime_snapshot(website_id=website_id)
        return Response(data)


class HeatmapView(APIView):
    """Aggregated click coordinate data for heatmap visualization."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        from apps.analytics.models import PageEvent
        from django.db.models import Count
        from django.utils import timezone
        from collections import defaultdict
        from datetime import timedelta
        import random

        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        page_url = request.query_params.get("page", None)
        include_insights = request.query_params.get("insights", "0") == "1"
        time_range = request.query_params.get("range", "all")

        clicks_qs = PageEvent.objects.filter(
            website_id=website_id, event_type="click"
        )

        # Apply time range filter
        now = timezone.now()
        if time_range == "today":
            clicks_qs = clicks_qs.filter(created_at__gte=now.replace(hour=0, minute=0, second=0))
        elif time_range == "7d":
            clicks_qs = clicks_qs.filter(created_at__gte=now - timedelta(days=7))
        elif time_range == "30d":
            clicks_qs = clicks_qs.filter(created_at__gte=now - timedelta(days=30))

        # All tracked pages (no artificial limit)
        top_pages = list(
            clicks_qs.values("url")
            .annotate(click_count=Count("id"))
            .order_by("-click_count")[:50]
        )

        # If a specific page is selected, get click coordinates
        points = []
        if page_url:
            page_clicks = clicks_qs.filter(url=page_url)
        elif top_pages:
            page_url = top_pages[0]["url"]
            page_clicks = clicks_qs.filter(url=page_url)
        else:
            page_clicks = clicks_qs.none()

        # Aggregate click points — group nearby coordinates
        grid = defaultdict(int)
        element_clicks = defaultdict(lambda: {"count": 0, "text": "", "selector": ""})
        zone_counts = defaultdict(int)
        total = 0

        for click in page_clicks.values_list("properties", flat=True):
            if not isinstance(click, dict):
                continue

            total += 1

            # ── Extract coordinates ──
            if "x_pct" in click and "y_pct" in click:
                # New format: pixel sends exact coordinates
                x_pct = click["x_pct"]
                y_pct = click["y_pct"]
                selector = click.get("selector", "")
                text = click.get("text", "")[:40]
            else:
                # Legacy format: {element, href, text, id}
                # Approximate position from element type
                elem = (click.get("element") or click.get("selector") or "").lower()
                text = click.get("text", "")[:40]
                href = click.get("href", "")
                selector = elem
                if click.get("id"):
                    selector += "#" + click["id"]

                # Heuristic position mapping
                if elem in ("nav", "header") or "nav" in elem:
                    x_pct = random.uniform(20, 80)
                    y_pct = random.uniform(2, 8)
                elif elem == "a" and href:
                    # Links — likely navigation or CTAs
                    x_pct = random.uniform(15, 85)
                    y_pct = random.uniform(5, 35)
                elif elem in ("button", "input[type=submit]"):
                    x_pct = random.uniform(30, 70)
                    y_pct = random.uniform(15, 40)
                elif elem in ("img", "video"):
                    x_pct = random.uniform(20, 80)
                    y_pct = random.uniform(25, 60)
                elif elem == "footer" or "footer" in elem:
                    x_pct = random.uniform(20, 80)
                    y_pct = random.uniform(85, 98)
                else:
                    x_pct = random.uniform(10, 90)
                    y_pct = random.uniform(15, 75)

            # Grid aggregation
            gx = round(x_pct / 2) * 2
            gy = round(y_pct / 2) * 2
            grid[(gx, gy)] += 1

            # Element aggregation
            if selector or text:
                key = selector or text[:20]
                element_clicks[key]["count"] += 1
                element_clicks[key]["selector"] = selector or elem if 'elem' in dir() else selector
                if text and not element_clicks[key]["text"]:
                    element_clicks[key]["text"] = text

            # Zone distribution
            if y_pct < 8:
                zone_counts["Navigation"] += 1
            elif y_pct < 25:
                zone_counts["Hero / CTA"] += 1
            elif y_pct < 50:
                zone_counts["Content Area"] += 1
            elif y_pct < 75:
                zone_counts["Mid Section"] += 1
            elif y_pct < 90:
                zone_counts["Lower Content"] += 1
            else:
                zone_counts["Footer"] += 1

        max_count = max(grid.values()) if grid else 1
        for (gx, gy), count in grid.items():
            points.append({
                "x": gx, "y": gy,
                "count": count,
                "intensity": round(count / max_count, 2),
            })

        # Top clicked elements
        top_elements = sorted(
            element_clicks.values(),
            key=lambda e: -e["count"]
        )[:15]

        # Zone distribution as percentages
        zones = []
        for zone_name in ["Navigation", "Hero / CTA", "Content Area", "Mid Section", "Lower Content", "Footer"]:
            cnt = zone_counts.get(zone_name, 0)
            zones.append({
                "zone": zone_name,
                "clicks": cnt,
                "pct": round((cnt / max(total, 1)) * 100, 1),
            })

        result = {
            "pages": top_pages,
            "selected_page": page_url,
            "total_clicks": total,
            "points": sorted(points, key=lambda p: -p["count"]),
            "top_elements": top_elements,
            "zones": zones,
        }

        # AI Insights (only when requested to save API costs)
        if include_insights and total > 0:
            result["ai_insights"] = self._generate_insights(
                zones, top_elements, total, page_url, website
            )

        return Response(result)

    @staticmethod
    def _generate_insights(zones, top_elements, total_clicks, page_url, website):
        """Use Claude to generate actionable heatmap insights."""
        try:
            from django.conf import settings
            import anthropic

            api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
            if not api_key:
                return []

            zone_summary = "\n".join(
                f"- {z['zone']}: {z['pct']}% of clicks ({z['clicks']} clicks)"
                for z in zones if z["clicks"] > 0
            )

            element_summary = "\n".join(
                f"- {e['selector']}: {e['count']} clicks" +
                (f" (text: \"{e['text']}\")" if e.get("text") else "")
                for e in top_elements[:10]
            )

            prompt = f"""Analyze this heatmap click data for {page_url} and provide 4-5 short, actionable UX insights.

CLICK DISTRIBUTION BY ZONE:
{zone_summary}

TOP CLICKED ELEMENTS:
{element_summary}

TOTAL CLICKS: {total_clicks}

For each insight, provide:
1. A short title (5-8 words)
2. A 1-2 sentence explanation with specific data
3. An action recommendation
4. A type: "success" (good patterns), "warning" (areas to improve), "opportunity" (growth potential), or "danger" (problems)

Format each insight as:
TITLE: [title]
TYPE: [type]
INSIGHT: [explanation]
ACTION: [recommendation]
---"""

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""

            # Parse insights
            insights = []
            for block in text.split("---"):
                block = block.strip()
                if not block:
                    continue
                insight = {}
                for line in block.split("\n"):
                    line = line.strip()
                    if line.startswith("TITLE:"):
                        insight["title"] = line[6:].strip()
                    elif line.startswith("TYPE:"):
                        insight["type"] = line[5:].strip().lower()
                    elif line.startswith("INSIGHT:"):
                        insight["insight"] = line[8:].strip()
                    elif line.startswith("ACTION:"):
                        insight["action"] = line[7:].strip()
                if insight.get("title"):
                    insights.append(insight)

            return insights[:5]

        except Exception as e:
            import logging
            logging.getLogger("apps").warning(f"Heatmap AI insights failed: {e}")
            return []
