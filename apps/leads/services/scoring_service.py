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


class ScoringService:
    @staticmethod
    def compute_score(*, visitor) -> int:
        """Compute lead score from visitor behavior."""
        from apps.analytics.models import PageEvent

        events = PageEvent.objects.filter(visitor=visitor)
        weights = DEFAULT_WEIGHTS

        score = 0
        pageview_count = events.filter(event_type="pageview").count()
        score += pageview_count * weights["page_views"]

        # High-intent pages
        for event in events.filter(event_type="pageview"):
            url_lower = event.url.lower()
            if "pricing" in url_lower:
                score += weights["pricing_page_visit"]
            elif "contact" in url_lower:
                score += weights["contact_page_visit"]

        form_submits = events.filter(event_type="form_submit").count()
        score += form_submits * weights["form_submit"]

        if visitor.visit_count > 1:
            score += weights["return_visit"]

        return min(score, 100)

    @staticmethod
    def rescore_website(*, website_id: str) -> int:
        """Rescore all visitors for a website and update their lead scores."""
        from apps.analytics.models import Visitor
        from apps.leads.models import Lead

        visitors = Visitor.objects.filter(website_id=website_id)
        updated = 0

        for visitor in visitors:
            new_score = ScoringService.compute_score(visitor=visitor)
            Visitor.objects.filter(pk=visitor.pk).update(lead_score=new_score)

            # Update or create lead if score is significant
            if new_score >= 10:
                Lead.objects.update_or_create(
                    visitor=visitor,
                    defaults={"website_id": website_id, "score": new_score},
                )
            updated += 1

        return updated
