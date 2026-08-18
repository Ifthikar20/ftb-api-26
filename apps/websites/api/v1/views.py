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


def _setup_state(user, website) -> dict:
    """Which setup step the user still owes before the dashboard has data.

    The dashboard renders guidance instead of empty cards until the user
    has completed audits, so it needs to know *which* step to point at.
    Returns the first incomplete step, or ``ready`` once results exist.
    """
    from apps.llm_ranking.models import LLMRankingAudit
    from apps.prompt_library.models import BrandPrompt

    if website is None:
        return {
            "step": "add_website",
            "title": "Add your website to get started",
            "body": "FetchBot measures how often AI assistants recommend your "
                    "brand. Add the site you want tracked and we'll scan it.",
            "cta_label": "Add a website",
            "cta_to": "/websites",
        }

    wid = str(website.id)

    if not BrandPrompt.objects.filter(website=website).exists():
        return {
            "step": "add_prompts",
            "title": "Build your prompt library",
            "body": "Prompts are the questions we ask each AI model on your "
                    "behalf. Add the ones your customers would actually ask.",
            "cta_label": "Add prompts",
            "cta_to": f"/llm-ranking/{wid}/prompts",
        }

    audits = LLMRankingAudit.objects.filter(created_by=user)
    if audits.filter(
        status__in=[LLMRankingAudit.STATUS_PENDING, LLMRankingAudit.STATUS_RUNNING],
    ).exists():
        return {
            "step": "audit_running",
            "title": "Your first audit is running",
            "body": "We're querying each AI model with your prompts. Results "
                    "appear on this page as soon as the run finishes.",
            # No CTA: the audit is already in flight and scheduling now lives
            # on this same page, so there is nowhere useful to send the user.
            "cta_label": "",
            "cta_to": "",
        }

    if not audits.filter(status=LLMRankingAudit.STATUS_COMPLETED).exists():
        return {
            "step": "run_audit",
            "title": "Run your first audit",
            "body": "Nothing has been measured yet. Use Run now above to see "
                    "which brands the AI models name — and where you place.",
            "cta_label": "",
            "cta_to": "",
        }

    return {"step": "ready"}


class DashboardView(APIView):
    """Aggregated dashboard stats for the logged-in user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.llm_ranking.services._window import (
            parse_csv_filter,
            parse_prompt_filter,
            resolve_window,
        )
        from apps.llm_ranking.services.geo_deep_dive import (
            build_for_user as build_deep_dive,
        )
        from apps.llm_ranking.services.geo_stats import (
            build_breakdowns_for_user,
            build_kpis_for_user,
        )
        from apps.llm_ranking.services.overview_stats import (
            build_filter_options,
            build_overview_for_user,
        )
        from apps.notifications.models import Notification

        websites = Website.objects.filter(user=request.user)
        website = websites.first()

        # Filters: ?range=overall|7d|30d|90d|1y|custom plus optional
        # ?start / ?end, ?prompts (newline-joined), and the pill filters
        # ?models / ?tags / ?topics (CSV or repeated params).
        range_key = request.query_params.get("range") or "30d"
        start_dt, end_dt = resolve_window(
            range_key,
            request.query_params.get("start"),
            request.query_params.get("end"),
        )
        prompt_filter = parse_prompt_filter(
            request.query_params.getlist("prompts") or request.query_params.get("prompts"),
        )
        models_filter = parse_csv_filter(
            request.query_params.getlist("models") or request.query_params.get("models"),
        )
        tags_filter = parse_csv_filter(
            request.query_params.getlist("tags") or request.query_params.get("tags"),
        )
        topics_filter = parse_csv_filter(
            request.query_params.getlist("topics") or request.query_params.get("topics"),
        )
        applied_filter = {
            "range": range_key,
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            "prompts": prompt_filter or [],
            "models": models_filter or [],
            "tags": tags_filter or [],
            "topics": topics_filter or [],
        }
        result_filters = {
            "prompts": prompt_filter,
            "providers": models_filter,
            "tags": tags_filter,
            "topics": topics_filter,
        }

        stats = build_kpis_for_user(
            request.user, start=start_dt, end=end_dt, **result_filters,
        ) or []
        analytics_breakdowns = build_breakdowns_for_user(
            request.user, start=start_dt, end=end_dt, **result_filters,
        )
        analytics_deep_dive = build_deep_dive(
            request.user, start=start_dt, end=end_dt, **result_filters,
        )

        # Recent activity (from notifications)
        activity = []
        for n in Notification.objects.filter(user=request.user)[:6]:
            color_map = {'hot_lead': 'var(--color-danger)', 'audit_complete': 'var(--color-success)', 'competitor_alert': 'var(--color-warning)', 'strategy': 'var(--color-info)', 'milestone': 'var(--color-success)', 'brand_security_alert': 'var(--color-danger)'}
            activity.append({'text': n.message, 'time': n.created_at.strftime('%b %d, %H:%M'), 'color': color_map.get(n.type, 'var(--text-muted)'), 'type': n.type})

        # Quick actions (static but driven by context)
        quick_actions = [
            {'label': 'Run Site Audit', 'desc': 'Check SEO, speed and security', 'to': '/websites'},
            {'label': 'Generate Strategy', 'desc': 'AI-powered growth plan', 'to': '/websites'},
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

        from apps.llm_ranking.services.visibility_series import (
            build_for_user as build_visibility_series,
        )
        visibility_series = build_visibility_series(request.user)

        # Overview tab: top brands, per-model matrix, cited domains. Returns
        # has_data=False with empty collections when nothing has been
        # measured yet so the frontend can render guidance rather than
        # placeholder numbers.
        overview = build_overview_for_user(
            request.user, start=start_dt, end=end_dt, **result_filters,
        )

        # Menu contents for the filter pills, computed from the unfiltered
        # window so a selected filter never hides its own options.
        filter_options = build_filter_options(
            request.user, start=start_dt, end=end_dt,
        )

        return Response({
            'stats': stats,
            'activity': activity,
            'quick_actions': quick_actions,
            'integrations': integrations,
            'visibility_series': visibility_series,
            'analytics_breakdowns': analytics_breakdowns,
            'analytics_deep_dive': analytics_deep_dive,
            'applied_filter': applied_filter,
            'overview': overview,
            'filter_options': filter_options,
            # Drives the dashboard's first-run guidance: which step the user
            # should take next when there is nothing to show yet.
            'setup_state': _setup_state(request.user, website),
        })


class OnboardingAssistView(APIView):
    """AI-assisted onboarding: generate description and topic suggestions from URL."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        import re

        from core.validators.safe_http import safe_get

        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        action = request.data.get("action", "describe")
        result = {}

        if action == "describe":
            # Attempt to scrape meta description and title from the URL
            description = request.data.get("current_description", "")
            if not description:
                try:
                    # website.url is user-controlled and this endpoint reflects
                    # the fetched title/meta back to the caller — a read-SSRF
                    # oracle if fetched raw. safe_get applies the SSRF guard and
                    # re-validates redirects (the old allow_redirects=True let a
                    # public host 302 to 169.254.169.254).
                    resp = safe_get(
                        website.url,
                        timeout=8,
                        max_bytes=20_000,
                        headers={"User-Agent": "FetchBot/1.0 (+https://fetchbot.ai/bot)"},
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

        return Response(result)

