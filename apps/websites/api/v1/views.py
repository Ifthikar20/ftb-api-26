from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.websites.models import Website
from apps.websites.services.website_service import WebsiteService
from apps.websites.services.pixel_service import PixelService
from apps.websites.services.verification_service import VerificationService
from apps.websites.api.v1.serializers import (
    WebsiteSerializer,
    WebsiteCreateSerializer,
    WebsiteUpdateSerializer,
    WebsiteSettingsSerializer,
)
from core.exceptions import ResourceNotFound
from apps.billing.services.plan_service import PLANS


class WebsiteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        websites = Website.objects.filter(user=request.user).order_by("-created_at")
        serializer = WebsiteSerializer(websites, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Enforce plan-based project limit
        current_count = Website.objects.filter(user=request.user).count()
        plan_id = "starter"
        try:
            plan_id = request.user.subscription.plan
        except Exception:
            pass
        plan_config = next((p for p in PLANS if p["id"] == plan_id), PLANS[0])
        max_projects = plan_config["limits"].get("websites", 1)
        if max_projects != -1 and current_count >= max_projects:
            return Response(
                {
                    "error": "project_limit_reached",
                    "message": f"Your {plan_config['name']} plan allows up to {max_projects} project(s). Upgrade to add more.",
                    "current": current_count,
                    "limit": max_projects,
                    "plan": plan_id,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = WebsiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        website = WebsiteService.create(user=request.user, **serializer.validated_data)
        return Response(WebsiteSerializer(website).data, status=status.HTTP_201_CREATED)


class WebsiteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_website(self, request, pk):
        return WebsiteService.get_for_user(user=request.user, website_id=pk)

    def get(self, request, pk):
        website = self._get_website(request, pk)
        return Response(WebsiteSerializer(website).data)

    def put(self, request, pk):
        website = self._get_website(request, pk)
        serializer = WebsiteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        website = WebsiteService.update(website=website, user=request.user, **serializer.validated_data)
        return Response(WebsiteSerializer(website).data)

    patch = put

    def delete(self, request, pk):
        website = self._get_website(request, pk)
        WebsiteService.delete(website=website, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PixelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        snippet = PixelService.get_snippet(website=website)
        return Response({"pixel_key": str(website.pixel_key), "snippet": snippet})


class PixelVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        result = VerificationService.verify_pixel(website=website)
        return Response(result)


class PixelRegenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        website = WebsiteService.regenerate_pixel_key(website=website, user=request.user)
        return Response({"pixel_key": str(website.pixel_key)})


class WebsiteSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        serializer = WebsiteSettingsSerializer(website.settings)
        return Response(serializer.data)

    def put(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        serializer = WebsiteSettingsSerializer(website.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DashboardView(APIView):
    """Aggregated dashboard stats for the logged-in user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.analytics.models import Visitor, PageEvent
        from apps.leads.models import Lead
        from apps.audits.models import Audit
        from apps.strategy.models import Strategy, Action, MorningBrief
        from apps.notifications.models import Notification

        websites = Website.objects.filter(user=request.user)
        website = websites.first()
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        # Stats
        total_visitors = 0
        hot_leads_count = 0
        growth_score = 0
        conversion_rate = 0
        visitors_prev = 0

        if website:
            total_visitors = Visitor.objects.filter(website=website, first_seen__gte=thirty_days_ago).count()
            visitors_prev = Visitor.objects.filter(website=website, first_seen__gte=thirty_days_ago - timedelta(days=30), first_seen__lt=thirty_days_ago).count()
            hot_leads_count = Lead.objects.filter(website=website, score__gte=70).count()
            latest_audit = Audit.objects.filter(website=website, status='completed').first()
            growth_score = latest_audit.overall_score if latest_audit else 0
            total_events = PageEvent.objects.filter(website=website, timestamp__gte=thirty_days_ago).count()
            form_events = PageEvent.objects.filter(website=website, event_type='form_submit', timestamp__gte=thirty_days_ago).count()
            conversion_rate = round((form_events / max(total_events, 1)) * 100, 1)

        visitor_change = 0
        if visitors_prev > 0:
            visitor_change = round(((total_visitors - visitors_prev) / visitors_prev) * 100, 1)

        stats = [
            {'label': 'Total Visitors', 'value': f'{total_visitors:,}', 'change': f'{abs(visitor_change)}% vs last month', 'direction': 'up' if visitor_change >= 0 else 'down'},
            {'label': 'Hot Leads', 'value': str(hot_leads_count), 'change': f'{hot_leads_count} above threshold', 'direction': 'up'},
            {'label': 'Growth Score', 'value': str(growth_score), 'change': 'from latest audit', 'direction': 'up' if growth_score >= 70 else 'down'},
            {'label': 'Conversion Rate', 'value': f'{conversion_rate}%', 'change': 'form submissions / events', 'direction': 'up' if conversion_rate >= 2 else 'down'},
        ]

        # Morning brief
        brief_text = ''
        if website:
            brief = MorningBrief.objects.filter(website=website).first()
            brief_text = brief.content if brief else 'No morning brief available yet. Run your first audit and let AI analyze your data.'

        # Actions
        actions = []
        if website:
            strategy = Strategy.objects.filter(website=website, status='active').first()
            if strategy:
                for a in strategy.actions.all()[:7]:
                    actions.append({'id': str(a.id), 'text': a.title, 'done': a.status == 'done', 'priority': a.estimated_impact.title() if a.estimated_impact else 'Medium'})

        # Recent activity (from notifications)
        activity = []
        for n in Notification.objects.filter(user=request.user)[:6]:
            color_map = {'hot_lead': 'var(--color-danger)', 'audit_complete': 'var(--color-success)', 'competitor_alert': 'var(--color-warning)', 'strategy': 'var(--color-info)', 'milestone': 'var(--color-success)'}
            activity.append({'text': n.message, 'time': n.created_at.strftime('%b %d, %H:%M'), 'color': color_map.get(n.type, 'var(--text-muted)'), 'type': n.type})

        # Quick actions (static but driven by context)
        quick_actions = [
            {'label': 'Run Site Audit', 'desc': 'Check SEO, speed and security', 'to': '/websites'},
            {'label': 'Generate Strategy', 'desc': 'AI-powered growth plan', 'to': '/websites'},
            {'label': 'View Hot Leads', 'desc': f'{hot_leads_count} leads above threshold', 'to': '/websites'},
            {'label': 'Competitor Intel', 'desc': 'See what changed this week', 'to': '/websites'},
        ]

        return Response({
            'stats': stats,
            'brief': brief_text,
            'actions': actions,
            'activity': activity,
            'quick_actions': quick_actions,
        })
