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
                pixel_key=pixel_key, event_data=request.data
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

        results = EventIngestionService.ingest_batch(pixel_key=pixel_key, events=events)
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
        from collections import defaultdict

        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        page_url = request.query_params.get("page", None)

        clicks_qs = PageEvent.objects.filter(
            website_id=website_id, event_type="click"
        )

        # Top pages by click count
        top_pages = list(
            clicks_qs.values("url")
            .annotate(click_count=Count("id"))
            .order_by("-click_count")[:10]
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
        total = 0
        for click in page_clicks.values_list("properties", flat=True):
            if isinstance(click, dict) and "x_pct" in click and "y_pct" in click:
                # Round to nearest 2% for grouping
                gx = round(click["x_pct"] / 2) * 2
                gy = round(click["y_pct"] / 2) * 2
                grid[(gx, gy)] += 1
                total += 1

        max_count = max(grid.values()) if grid else 1
        for (gx, gy), count in grid.items():
            points.append({
                "x": gx, "y": gy,
                "count": count,
                "intensity": round(count / max_count, 2),
            })

        return Response({
            "pages": top_pages,
            "selected_page": page_url,
            "total_clicks": total,
            "points": sorted(points, key=lambda p: -p["count"]),
        })
