from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.analytics.services.event_ingestion_service import EventIngestionService
from apps.analytics.services.analytics_service import AnalyticsService
from apps.websites.services.website_service import WebsiteService
from core.interceptors.throttling import PixelIngestThrottle


class EventIngestView(APIView):
    """Public pixel ingestion endpoint."""
    permission_classes = [AllowAny]
    throttle_classes = [PixelIngestThrottle]

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
