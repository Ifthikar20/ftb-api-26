import json

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.event_ingestion_service import EventIngestionService
from apps.analytics.services.origin_check import is_origin_allowed
from apps.websites.models import Website
from core.interceptors.throttling import PixelIngestThrottle
from core.views import TenantScopedAPIView

# A single pixel event is a few hundred bytes; a batch of 50 a few KB.
# Anything past this on the public endpoint is abuse, so we reject before
# parsing rather than buffering it.
MAX_INGEST_BODY_BYTES = 64 * 1024


def _reject_oversized_body(request):
    """Return a 413 Response if the request body exceeds the ingest cap."""
    try:
        length = int(request.META.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    if length > MAX_INGEST_BODY_BYTES:
        return Response(
            {"error": "payload too large"},
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    return None


def _resolve_website_or_403(pixel_key, request):
    """Return (website, error_response).

    ``error_response`` is None on success, or a DRF Response (403/400) the
    caller should return immediately. Bundles three rejections:
    pixel_key missing, pixel_key unknown, or Origin not on the allowlist.
    """
    if not pixel_key:
        return None, Response(
            {"error": "pixel_key required"}, status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        website = Website.objects.only("id", "url", "pixel_key", "is_active").get(
            pixel_key=pixel_key, is_active=True,
        )
    except Website.DoesNotExist:
        # Treat unknown keys as forbidden, not 400 — refusing to confirm
        # whether the key exists makes brute-forcing slower.
        return None, Response(
            {"error": "forbidden"}, status=status.HTTP_403_FORBIDDEN,
        )
    if not is_origin_allowed(request, website):
        return None, Response(
            {"error": "origin not allowed"}, status=status.HTTP_403_FORBIDDEN,
        )
    return website, None


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
        oversized = _reject_oversized_body(request)
        if oversized is not None:
            return oversized
        pixel_key = request.data.get("pixel_key")
        _website, err = _resolve_website_or_403(pixel_key, request)
        if err is not None:
            return err

        try:
            EventIngestionService.ingest_event(
                pixel_key=pixel_key, event_data=request.data, request=request,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"ok": True}, status=status.HTTP_202_ACCEPTED)


class BatchEventIngestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PixelIngestThrottle]
    parser_classes = [JSONParser, PlainTextJSONParser, FormParser]  # type: ignore[assignment]

    def post(self, request):
        oversized = _reject_oversized_body(request)
        if oversized is not None:
            return oversized
        pixel_key = request.data.get("pixel_key")
        events = request.data.get("events", [])
        if not isinstance(events, list) or not events:
            return Response(
                {"error": "events required"}, status=status.HTTP_400_BAD_REQUEST,
            )
        _website, err = _resolve_website_or_403(pixel_key, request)
        if err is not None:
            return err

        results = EventIngestionService.ingest_batch(
            pixel_key=pixel_key, events=events, request=request,
        )
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
