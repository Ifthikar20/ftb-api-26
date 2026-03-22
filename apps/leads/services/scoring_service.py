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
        """Rescore all visitors for a website and update their lead scores."""
        from apps.analytics.models import Visitor
        from apps.leads.models import Lead, ScoringConfig
        from apps.websites.models import Website

        website = Website.objects.select_related("user").get(id=website_id)
        visitors = Visitor.objects.filter(website_id=website_id)
        updated = 0

        # Determine hot-lead threshold (per-website config or global default)
        try:
            config = ScoringConfig.objects.get(website_id=website_id)
            threshold = config.threshold
        except ScoringConfig.DoesNotExist:
            threshold = 70

        for visitor in visitors:
            old_score = visitor.lead_score
            new_score = ScoringService.compute_score(visitor=visitor)
            Visitor.objects.filter(pk=visitor.pk).update(lead_score=new_score)

            # Update or create lead if score is significant
            if new_score >= 10:
                lead, created = Lead.objects.update_or_create(
                    visitor=visitor,
                    defaults={"website_id": website_id, "score": new_score},
                )
                # Fire hot-lead notifications when score first crosses threshold
                if new_score >= threshold and old_score < threshold:
                    try:
                        from apps.notifications.services.notification_service import (
                            NotificationService,
                        )
                        from apps.websites.models import WebsiteSettings

                        # Respect website-level notification setting
                        try:
                            ws = WebsiteSettings.objects.get(website_id=website_id)
                            if not ws.notify_hot_leads:
                                continue
                        except WebsiteSettings.DoesNotExist:
                            pass

                        NotificationService.fire_hot_lead(user=website.user, lead=lead)
                    except Exception as e:
                        logger.error("Hot-lead notification failed for lead %s: %s", lead.id, e)

            updated += 1

        return updated
