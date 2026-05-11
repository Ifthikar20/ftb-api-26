import json

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.event_ingestion_service import EventIngestionService
from core.interceptors.throttling import PixelIngestThrottle
from core.views import TenantScopedAPIView


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
    parser_classes = [JSONParser, PlainTextJSONParser, FormParser]  # type: ignore[assignment]

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
    parser_classes = [JSONParser, PlainTextJSONParser, FormParser]  # type: ignore[assignment]

    def post(self, request):
        pixel_key = request.data.get("pixel_key")
        events = request.data.get("events", [])
        if not pixel_key or not events:
            return Response({"error": "pixel_key and events required"}, status=status.HTTP_400_BAD_REQUEST)

        results = EventIngestionService.ingest_batch(pixel_key=pixel_key, events=events, request=request)
        return Response({"ingested": len(results)}, status=status.HTTP_202_ACCEPTED)


class AnalyticsOverviewView(TenantScopedAPIView):
    def get(self, request, website_id):
        self.get_website(website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_overview(website_id=website_id, period=period)
        return Response(data)


class TopPagesView(TenantScopedAPIView):
    def get(self, request, website_id):
        self.get_website(website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_top_pages(website_id=website_id, period=period)
        return Response(data)


class TrafficSourcesView(TenantScopedAPIView):
    def get(self, request, website_id):
        self.get_website(website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_traffic_sources(website_id=website_id, period=period)
        return Response(data)


class RealtimeView(TenantScopedAPIView):
    def get(self, request, website_id):
        self.get_website(website_id)
        data = AnalyticsService.get_realtime_snapshot(website_id=website_id)
        return Response(data)


class AITrafficView(TenantScopedAPIView):
    """AI-sourced traffic breakdown (sessions from ChatGPT, Claude, etc.)."""

    def get(self, request, website_id):
        self.get_website(website_id)
        period = request.query_params.get("period", "30d")
        data = AnalyticsService.get_ai_traffic_summary(website_id=website_id, period=period)
        return Response(data)
