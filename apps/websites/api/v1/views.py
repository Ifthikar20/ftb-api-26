from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.websites.api.v1.serializers import (
    WebsiteCreateSerializer,
    WebsiteSerializer,
    WebsiteSettingsSerializer,
    WebsiteUpdateSerializer,
)
from apps.websites.models import Website
from apps.websites.services.pixel_service import PixelService
from apps.websites.services.verification_service import VerificationService
from apps.websites.services.website_service import WebsiteService


class WebsiteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        websites = Website.objects.filter(user=request.user).order_by("-created_at")
        serializer = WebsiteSerializer(websites, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Plan limit check disabled for testing — re-enable for production
        # current_count = Website.objects.filter(user=request.user).count()
        # plan_id = "starter"
        # try:
        #     plan_id = request.user.subscription.plan
        # except Exception:
        #     pass
        # plan_config = next((p for p in PLANS if p["id"] == plan_id), PLANS[0])
        # max_projects = plan_config["limits"].get("websites", 1)
        # if max_projects != -1 and current_count >= max_projects:
        #     return Response(
        #         {
        #             "error": "project_limit_reached",
        #             "message": f"Your {plan_config['name']} plan allows up to {max_projects} project(s). Upgrade to add more.",
        #             "current": current_count,
        #             "limit": max_projects,
        #             "plan": plan_id,
        #         },
        #         status=status.HTTP_403_FORBIDDEN,
        #     )
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
        from apps.analytics.models import PageEvent, Visitor
        from apps.leads.models import Lead
        from apps.notifications.models import Notification

        websites = Website.objects.filter(user=request.user)
        website = websites.first()
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        now - timedelta(days=7)

        # Stats
        total_visitors = 0
        hot_leads_count = 0
        conversion_rate = 0
        visitors_prev = 0

        if website:
            total_visitors = Visitor.objects.filter(website=website, first_seen__gte=thirty_days_ago).count()
            visitors_prev = Visitor.objects.filter(website=website, first_seen__gte=thirty_days_ago - timedelta(days=30), first_seen__lt=thirty_days_ago).count()
            hot_leads_count = Lead.objects.filter(website=website, score__gte=70).count()
            total_events = PageEvent.objects.filter(website=website, timestamp__gte=thirty_days_ago).count()
            form_events = PageEvent.objects.filter(website=website, event_type='form_submit', timestamp__gte=thirty_days_ago).count()
            conversion_rate = round((form_events / max(total_events, 1)) * 100, 1)

        visitor_change = 0
        if visitors_prev > 0:
            visitor_change = round(((total_visitors - visitors_prev) / visitors_prev) * 100, 1)

        stats = [
            {'label': 'Total Visitors', 'value': f'{total_visitors:,}', 'change': f'{abs(visitor_change)}% vs last month', 'direction': 'up' if visitor_change >= 0 else 'down'},
            {'label': 'Hot Leads', 'value': str(hot_leads_count), 'change': f'{hot_leads_count} above threshold', 'direction': 'up'},
            {'label': 'Conversion Rate', 'value': f'{conversion_rate}%', 'change': 'form submissions / events', 'direction': 'up' if conversion_rate >= 2 else 'down'},
        ]

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

        # Integration status
        from apps.websites.models import Integration
        integration_types = [
            ('ga', 'Google Analytics'),
            ('gsc', 'Google Search Console'),
            ('facebook', 'Facebook Ads'),
        ]
        services = []
        for itype, label in integration_types:
            integration = Integration.objects.filter(website=website, type=itype, is_active=True).first() if website else None
            services.append({
                'type': itype,
                'label': label,
                'connected': integration is not None,
                'connected_at': integration.connected_at.strftime('%b %d, %Y') if integration else None,
            })

        integrations = {
            'pixel': {
                'installed': website.pixel_verified if website else False,
                'verified': website.pixel_verified if website else False,
                'verified_at': website.pixel_verified_at.strftime('%b %d, %Y') if website and website.pixel_verified_at else None,
                'pixel_key': str(website.pixel_key) if website else None,
            },
            'services': services,
        }

        return Response({
            'stats': stats,
            'activity': activity,
            'quick_actions': quick_actions,
            'integrations': integrations,
        })


class OnboardingAssistView(APIView):
    """AI-assisted onboarding: generate description and topic suggestions from URL."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        import re

        import requests as http_requests

        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        action = request.data.get("action", "describe")
        result = {}

        if action == "describe":
            # Attempt to scrape meta description and title from the URL
            description = request.data.get("current_description", "")
            if not description:
                try:
                    resp = http_requests.get(
                        website.url,
                        timeout=8,
                        headers={"User-Agent": "FetchBot/1.0"},
                        allow_redirects=True,
                    )
                    html = resp.text[:20000]
                    # Extract meta description
                    meta_match = re.search(
                        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
                        html, re.IGNORECASE,
                    )
                    title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
                    parts = []
                    if title_match:
                        parts.append(title_match.group(1).strip())
                    if meta_match:
                        parts.append(meta_match.group(1).strip())
                    description = ". ".join(parts) if parts else f"{website.name} — {website.url}"
                except Exception:
                    description = f"{website.name} is a business at {website.url}."

            result["description"] = description

        elif action == "topics":
            # Generate topic suggestions based on business description and industry
            desc = request.data.get("description", website.description or "")
            industry = request.data.get("industry", website.industry or "")

            # Heuristic-based topic generation from description keywords
            base_topics = []
            desc_lower = (desc + " " + industry).lower()

            topic_map = {
                "saas": ["SaaS Solutions", "Cloud-Based Tools", "B2B Software"],
                "security": ["Cybersecurity Solutions", "Security Testing Tools", "Vulnerability Assessment"],
                "marketing": ["Digital Marketing Tools", "Marketing Automation", "Growth Analytics"],
                "e-commerce": ["E-Commerce Platforms", "Online Retail Solutions", "Shopping Tools"],
                "ecommerce": ["E-Commerce Platforms", "Online Retail Solutions", "Shopping Tools"],
                "ai": ["AI-Powered Tools", "Machine Learning Solutions", "Intelligent Automation"],
                "analytics": ["Data Analytics Platforms", "Business Intelligence", "Performance Tracking"],
                "health": ["Health & Wellness Tech", "Healthcare Solutions", "Medical Technology"],
                "finance": ["Financial Technology", "Payment Solutions", "Fintech Platforms"],
                "education": ["EdTech Solutions", "Online Learning Platforms", "Educational Tools"],
                "design": ["Design Tools", "Creative Platforms", "UI/UX Solutions"],
                "real estate": ["Real Estate Technology", "Property Management", "PropTech Solutions"],
                "food": ["Food & Beverage Tech", "Restaurant Solutions", "FoodTech"],
                "travel": ["Travel Technology", "Booking Platforms", "Hospitality Solutions"],
                "legal": ["Legal Technology", "LegalTech Solutions", "Law Practice Tools"],
                "hr": ["HR Technology", "People Management", "Talent Solutions"],
                "construction": ["Construction Technology", "ConTech Solutions", "Project Management"],
                "logistics": ["Logistics Solutions", "Supply Chain Tech", "Shipping & Delivery"],
                "gaming": ["Gaming Technology", "Game Development Tools", "Interactive Entertainment"],
                "social": ["Social Media Tools", "Community Platforms", "Social Commerce"],
                "consulting": ["Business Consulting", "Management Advisory", "Strategy Consulting"],
                "automation": ["Business Automation", "Workflow Automation", "Process Optimization"],
                "crm": ["CRM Solutions", "Customer Management", "Sales Enablement"],
                "seo": ["SEO Tools", "Search Optimization", "Content Strategy"],
                "content": ["Content Marketing", "Content Management", "Digital Publishing"],
                "video": ["Video Technology", "Streaming Solutions", "Video Production"],
                "testing": ["Software Testing", "QA Automation", "Quality Assurance"],
                "devops": ["DevOps Tools", "CI/CD Platforms", "Infrastructure Management"],
                "cloud": ["Cloud Services", "Infrastructure as a Service", "Cloud Management"],
            }

            for keyword, topics in topic_map.items():
                if keyword in desc_lower:
                    base_topics.extend(topics)

            # Always add some generic industry topics
            if industry:
                base_topics.extend([
                    f"Best {industry} Tools",
                    f"Top {industry} Solutions",
                    f"{industry} Recommendations",
                ])

            # Deduplicate and limit
            seen = set()
            unique_topics = []
            for t in base_topics:
                if t.lower() not in seen:
                    seen.add(t.lower())
                    unique_topics.append(t)

            # If we have very few, add generics
            generic_fallbacks = [
                "Industry-Leading Solutions",
                "Top Recommended Tools",
                "Best in Class Services",
                "Expert-Recommended Platforms",
                "Innovative Business Solutions",
            ]
            while len(unique_topics) < 5:
                fallback = generic_fallbacks.pop(0)
                if fallback.lower() not in seen:
                    unique_topics.append(fallback)
                    seen.add(fallback.lower())

            result["topics"] = unique_topics[:10]

        elif action == "competitors":
            # Try to discover competitors automatically
            from apps.competitors.services.discovery_service import DiscoveryService
            discovered = DiscoveryService.auto_detect(website=website)
            result["competitors"] = discovered

        return Response(result)

