"""Advanced analytics API views."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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


class EngagementMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.retention_service import RetentionService
        period = request.query_params.get("period", "30d")
        data = RetentionService.get_engagement_metrics(
            website_id=website_id, period=period
        )
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
        from django.db.models import Count

        from apps.analytics.models import Visitor

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
        from datetime import timedelta

        from django.utils import timezone

        from apps.analytics.models import PageEvent

        cutoff = timezone.now() - timedelta(seconds=120)
        events = (
            PageEvent.objects.filter(
                website_id=website_id, timestamp__gte=cutoff
            )
            .order_by("-timestamp")[:50]
            .values("id", "event_type", "event_name", "url", "timestamp", "visitor__fingerprint_hash")
        )
        return Response(list(events))


# Maximum window we ever serve from this endpoint. Mirrors the UI claim
# in AnalyticsPage that we retain analytics + event logs for the most
# recent six months. The pixel ingestion task already purges older
# rows; this clamp is belt-and-suspenders.
EVENT_LOG_RETENTION_DAYS = 180


class EventLogView(APIView):
    """Persisted, paginated event log for the SEO Analytics Events tab.

    Returns rows straight out of PageEvent, in reverse-chronological order,
    with optional filters and an in-window CSV export.

    Query params
    ------------
    page         page number, 1-indexed (default 1)
    page_size    rows per page, capped at 500 (default 50)
    event_type   one of pageview / click / scroll / form_submit / ...
    device       desktop / mobile / tablet (matched on Visitor.device_type)
    country      ISO-2 code, matched on Visitor.geo_country
    q            free-text search across url, event_name, fingerprint
    start, end   ISO timestamps; clamped to the last 180 days
    format       set to 'csv' to download instead of paginate
    """

    permission_classes = [IsAuthenticated]

    PAGE_SIZE_DEFAULT = 50
    PAGE_SIZE_MAX = 500

    EVENT_FIELDS = [
        "id", "event_type", "event_name", "url", "referrer",
        "timestamp", "scroll_depth", "time_on_page_ms",
        "visitor__fingerprint_hash",
        "visitor__device_type",
        "visitor__geo_country",
        "visitor__geo_city",
    ]

    def get(self, request, website_id):
        import datetime as _dt

        from django.db.models import Q
        from django.utils import timezone

        from apps.analytics.models import PageEvent

        WebsiteService.get_for_user(user=request.user, website_id=website_id)

        retention_floor = timezone.now() - _dt.timedelta(days=EVENT_LOG_RETENTION_DAYS)

        qs = PageEvent.objects.filter(
            website_id=website_id,
            timestamp__gte=retention_floor,
        )

        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        device = request.query_params.get("device")
        if device:
            qs = qs.filter(visitor__device_type__iexact=device)

        country = request.query_params.get("country")
        if country:
            qs = qs.filter(visitor__geo_country__iexact=country)

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(url__icontains=q)
                | Q(event_name__icontains=q)
                | Q(visitor__fingerprint_hash__icontains=q),
            )

        start = request.query_params.get("start")
        if start:
            try:
                start_dt = _dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                qs = qs.filter(timestamp__gte=max(start_dt, retention_floor))
            except (TypeError, ValueError):
                pass
        end = request.query_params.get("end")
        if end:
            try:
                end_dt = _dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
                qs = qs.filter(timestamp__lte=end_dt)
            except (TypeError, ValueError):
                pass

        qs = qs.order_by("-timestamp")

        if (request.query_params.get("format") or "").lower() == "csv":
            return self._stream_csv(qs)

        try:
            page = max(1, int(request.query_params.get("page", "1")))
        except ValueError:
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", self.PAGE_SIZE_DEFAULT))
        except ValueError:
            page_size = self.PAGE_SIZE_DEFAULT
        page_size = max(1, min(page_size, self.PAGE_SIZE_MAX))

        total = qs.count()
        offset = (page - 1) * page_size
        rows = list(qs.values(*self.EVENT_FIELDS)[offset:offset + page_size])

        return Response({
            "results": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
            "retention_days": EVENT_LOG_RETENTION_DAYS,
        })

    def _stream_csv(self, qs):
        import csv

        from django.http import StreamingHttpResponse

        class _Echo:
            def write(self, value):
                return value

        writer = csv.writer(_Echo())
        header = [
            "timestamp", "event_type", "event_name", "url", "referrer",
            "scroll_depth", "time_on_page_ms",
            "visitor_fingerprint", "device_type", "country", "city",
        ]

        def _rows():
            yield writer.writerow(header)
            for row in qs.values_list(
                "timestamp", "event_type", "event_name", "url", "referrer",
                "scroll_depth", "time_on_page_ms",
                "visitor__fingerprint_hash",
                "visitor__device_type",
                "visitor__geo_country",
                "visitor__geo_city",
            ).iterator(chunk_size=2000):
                yield writer.writerow(row)

        response = StreamingHttpResponse(_rows(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="event-log.csv"'
        return response


class AnalyticsAccessLogView(APIView):
    """Who has read this website's analytics, and when.

    Scoped exactly like every other analytics view: the caller must own the
    website. Returns the access trail in reverse-chronological order so a
    customer (or their security team) can verify that only authorized users
    have viewed their data. This is the compliance read side of the audit
    trail the AnalyticsAccessLogMiddleware writes.
    """

    permission_classes = [IsAuthenticated]
    PAGE_SIZE_DEFAULT = 50
    PAGE_SIZE_MAX = 200

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.models import AnalyticsAccessLog

        qs = AnalyticsAccessLog.objects.filter(
            website_id_raw=str(website_id),
        ).order_by("-accessed_at")

        try:
            page = max(1, int(request.query_params.get("page", "1")))
        except ValueError:
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", self.PAGE_SIZE_DEFAULT))
        except ValueError:
            page_size = self.PAGE_SIZE_DEFAULT
        page_size = max(1, min(page_size, self.PAGE_SIZE_MAX))

        total = qs.count()
        offset = (page - 1) * page_size
        rows = list(
            qs.values(
                "id", "user_email", "path", "method", "status_code",
                "ip_address", "user_agent", "accessed_at",
            )[offset:offset + page_size]
        )
        return Response({
            "results": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
        })
