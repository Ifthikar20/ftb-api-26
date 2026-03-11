"""Advanced analytics API views."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.websites.services.website_service import WebsiteService


class ChartDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.daily_stats import DailyStatsService
        period = request.query_params.get("period", "30d")
        data = DailyStatsService.get_chart_data(website_id=website_id, period=period)
        return Response(data)


class DeviceBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.daily_stats import DailyStatsService
        period = request.query_params.get("period", "30d")
        data = DailyStatsService.get_device_breakdown(website_id=website_id, period=period)
        return Response(data)


class CountryBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.daily_stats import DailyStatsService
        period = request.query_params.get("period", "30d")
        data = DailyStatsService.get_country_breakdown(website_id=website_id, period=period)
        return Response(data)


class FunnelListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.funnel_service import FunnelService
        data = FunnelService.list_funnels(website_id=website_id)
        return Response(data)

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.funnel_service import FunnelService
        name = request.data.get("name", "New Funnel")
        steps = request.data.get("steps", [])
        data = FunnelService.create_funnel(
            website_id=website_id, name=name, steps=steps, user=request.user
        )
        return Response(data, status=status.HTTP_201_CREATED)


class FunnelCalculateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, funnel_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.funnel_service import FunnelService
        period = request.query_params.get("period", "30d")
        data = FunnelService.calculate_funnel(
            website_id=website_id, funnel_id=funnel_id, period=period
        )
        return Response(data)


class RetentionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.retention_service import RetentionService
        weeks = int(request.query_params.get("weeks", 8))
        data = RetentionService.get_retention_matrix(website_id=website_id, num_weeks=weeks)
        return Response(data)


class RetentionCurveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.retention_service import RetentionService
        weeks = int(request.query_params.get("weeks", 8))
        data = RetentionService.get_retention_curve(website_id=website_id, num_weeks=weeks)
        return Response(data)


class FlowView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.flow_service import FlowService
        period = request.query_params.get("period", "30d")
        data = FlowService.get_user_flows(website_id=website_id, period=period)
        return Response(data)


class EntryExitPagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.flow_service import FlowService
        period = request.query_params.get("period", "30d")
        entry = FlowService.get_entry_pages(website_id=website_id, period=period)
        exit_ = FlowService.get_exit_pages(website_id=website_id, period=period)
        return Response({"entry_pages": entry, "exit_pages": exit_})


class VisitorJourneysView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.flow_service import FlowService
        period = request.query_params.get("period", "30d")
        data = FlowService.get_visitor_journeys(website_id=website_id, period=period)
        return Response(data)


class VisitorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.models import Visitor
        from django.db.models import Count

        visitors = (
            Visitor.objects.filter(website_id=website_id)
            .annotate(event_count=Count("events"))
            .order_by("-last_seen")[:100]
            .values(
                "id", "fingerprint_hash", "company_name", "geo_country",
                "geo_city", "device_type", "browser", "os",
                "first_seen", "last_seen", "visit_count", "lead_score", "event_count",
            )
        )
        return Response(list(visitors))


class VisitorTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, visitor_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.models import PageEvent

        events = (
            PageEvent.objects.filter(
                website_id=website_id, visitor_id=visitor_id
            )
            .order_by("-timestamp")[:200]
            .values("id", "event_type", "event_name", "url", "timestamp", "properties", "scroll_depth", "time_on_page_ms")
        )
        return Response(list(events))


class AIInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.ai_insights_service import AIInsightsService
        insights = AIInsightsService.generate_insights(website_id=website_id)
        actions = AIInsightsService.suggest_actions(website_id=website_id)
        return Response({"insights": insights, "actions": actions})


class LiveEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.models import PageEvent
        from datetime import timedelta
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(seconds=120)
        events = (
            PageEvent.objects.filter(
                website_id=website_id, timestamp__gte=cutoff
            )
            .order_by("-timestamp")[:50]
            .values("id", "event_type", "event_name", "url", "timestamp", "visitor__fingerprint_hash")
        )
        return Response(list(events))
