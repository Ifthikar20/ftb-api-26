import logging

logger = logging.getLogger("apps")

DEFAULT_WEIGHTS = {
    "page_views": 2,
    "pricing_page_visit": 20,
    "contact_page_visit": 15,
    "form_submit": 30,
    "return_visit": 10,
    "time_on_site_min": 1,  # points per minute
    "high_scroll_depth": 5,
}

HIGH_SCROLL_DEPTH_THRESHOLD = 75  # percent


class ScoringService:
    @staticmethod
    def compute_score(*, visitor) -> int:
        """Compute lead score from visitor behavior."""
        from apps.analytics.models import PageEvent
        from apps.leads.models import ScoringConfig

        events = PageEvent.objects.filter(visitor=visitor)

        # Use per-website scoring weights if configured
        try:
            config = ScoringConfig.objects.get(website_id=visitor.website_id)
            weights = {**DEFAULT_WEIGHTS, **config.weights} if config.weights else DEFAULT_WEIGHTS
        except ScoringConfig.DoesNotExist:
            weights = DEFAULT_WEIGHTS

        score = 0
        pageview_events = events.filter(event_type="pageview")
        pageview_count = pageview_events.count()
        score += pageview_count * weights["page_views"]

        # High-intent pages
        for event in pageview_events:
            url_lower = event.url.lower()
            if "pricing" in url_lower:
                score += weights["pricing_page_visit"]
            elif "contact" in url_lower:
                score += weights["contact_page_visit"]

        form_submits = events.filter(event_type="form_submit").count()
        score += form_submits * weights["form_submit"]

        if visitor.visit_count > 1:
            score += weights["return_visit"]

        # Time on site (sum of time_on_page_ms across all events, convert to minutes)
        time_on_page_total_ms = (
            events.filter(time_on_page_ms__isnull=False)
            .values_list("time_on_page_ms", flat=True)
        )
        total_minutes = sum(time_on_page_total_ms) / 60000 if time_on_page_total_ms else 0
        score += int(total_minutes) * weights["time_on_site_min"]

        # High scroll depth (any event with scroll_depth >= threshold)
        if events.filter(scroll_depth__gte=HIGH_SCROLL_DEPTH_THRESHOLD).exists():
            score += weights["high_scroll_depth"]

        return min(score, 100)

    @staticmethod
    def rescore_website(*, website_id: str) -> int:
        """Rescore all visitors for a website using bulk aggregation (no N+1)."""
        from django.db.models import Case, Count, IntegerField, Max, Q, Sum, When

        from apps.analytics.models import PageEvent, Visitor
        from apps.leads.models import Lead, ScoringConfig
        from apps.websites.models import Website

        website = Website.objects.select_related("user").get(id=website_id)

        # Determine hot-lead threshold (per-website config or global default)
        try:
            config = ScoringConfig.objects.get(website_id=website_id)
            threshold = config.threshold
            weights = {**DEFAULT_WEIGHTS, **(config.weights or {})}
        except ScoringConfig.DoesNotExist:
            threshold = 70
            weights = DEFAULT_WEIGHTS

        # ── Single aggregation query: compute all scoring signals per visitor ──
        visitor_stats = (
            PageEvent.objects.filter(website_id=website_id)
            .values("visitor_id")
            .annotate(
                pageview_count=Count(
                    "id", filter=Q(event_type="pageview")
                ),
                pricing_page_count=Count(
                    "id",
                    filter=Q(event_type="pageview", url__icontains="pricing"),
                ),
                contact_page_count=Count(
                    "id",
                    filter=Q(event_type="pageview", url__icontains="contact"),
                ),
                form_submit_count=Count(
                    "id", filter=Q(event_type="form_submit")
                ),
                max_scroll_depth=Max("scroll_depth"),
                total_time_ms=Sum(
                    Case(
                        When(time_on_page_ms__isnull=False, then="time_on_page_ms"),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
            )
        )

        # Index by visitor_id for O(1) lookup
        stats_by_visitor = {s["visitor_id"]: s for s in visitor_stats}

        # Fetch all visitors with their current scores
        visitors = Visitor.objects.filter(website_id=website_id).values_list(
            "pk", "lead_score", "visit_count"
        )

        updated = 0
        visitors_to_update = []
        leads_to_notify = []

        for visitor_pk, old_score, visit_count in visitors:
            stats = stats_by_visitor.get(visitor_pk, {})

            score = 0
            score += stats.get("pageview_count", 0) * weights["page_views"]
            score += stats.get("pricing_page_count", 0) * weights["pricing_page_visit"]
            score += stats.get("contact_page_count", 0) * weights["contact_page_visit"]
            score += stats.get("form_submit_count", 0) * weights["form_submit"]

            if visit_count > 1:
                score += weights["return_visit"]

            total_minutes = (stats.get("total_time_ms", 0) or 0) / 60000
            score += int(total_minutes) * weights["time_on_site_min"]

            max_scroll = stats.get("max_scroll_depth") or 0
            if max_scroll >= HIGH_SCROLL_DEPTH_THRESHOLD:
                score += weights["high_scroll_depth"]

            new_score = min(score, 100)

            visitors_to_update.append((visitor_pk, new_score, old_score))
            updated += 1

        # ── Bulk update visitors ──
        for visitor_pk, new_score, _ in visitors_to_update:
            Visitor.objects.filter(pk=visitor_pk).update(lead_score=new_score)

        # ── Update or create leads, fire notifications ──
        for visitor_pk, new_score, old_score in visitors_to_update:
            if new_score >= 10:
                lead, created = Lead.objects.update_or_create(
                    visitor_id=visitor_pk,
                    defaults={"website_id": website_id, "score": new_score},
                )
                # Fire hot-lead notification when score first crosses threshold
                if new_score >= threshold and old_score < threshold:
                    try:
                        from apps.notifications.services.notification_service import (
                            NotificationService,
                        )
                        from apps.websites.models import WebsiteSettings

                        try:
                            ws = WebsiteSettings.objects.get(website_id=website_id)
                            if not ws.notify_hot_leads:
                                continue
                        except WebsiteSettings.DoesNotExist:
                            pass

                        NotificationService.fire_hot_lead(user=website.user, lead=lead)
                    except Exception as e:
                        logger.error("Hot-lead notification failed for lead %s: %s", lead.id, e)

        return updated
