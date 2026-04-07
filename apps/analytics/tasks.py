import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.analytics.tasks.aggregate_hourly_metrics")
def aggregate_hourly_metrics():
    """Pre-aggregate hourly analytics data."""
    from apps.analytics.services.aggregation_service import AggregationService
    from apps.websites.models import Website

    for website in Website.objects.filter(is_active=True):
        try:
            AggregationService.aggregate_hourly(website_id=str(website.id))
        except Exception as e:
            logger.error(f"Aggregation failed for website {website.id}: {e}")


@shared_task(name="apps.analytics.tasks.check_keyword_alerts")
def check_keyword_alerts():
    """
    Runs on a schedule (e.g. every hour via celery-beat).
    For every active KeywordAlert, checks whether the associated keyword(s)
    have moved enough positions to trigger the alert.
    """
    from django.utils import timezone

    from apps.analytics.models import KeywordAlert, KeywordAlertEvent, TrackedKeyword

    for alert in KeywordAlert.objects.filter(is_active=True).select_related("tracked_keyword", "website"):
        if alert.tracked_keyword:
            keywords = [alert.tracked_keyword]
        else:
            keywords = list(TrackedKeyword.objects.filter(website=alert.website))

        for kw in keywords:
            if kw.current_rank is None or kw.previous_rank is None:
                continue
            # Positive change = rank number went DOWN = improved position
            change = kw.previous_rank - kw.current_rank
            abs_change = abs(change)
            if abs_change < alert.threshold:
                continue
            if alert.direction == KeywordAlert.DIRECTION_IMPROVED and change <= 0:
                continue
            if alert.direction == KeywordAlert.DIRECTION_DECLINED and change >= 0:
                continue

            # Create the event record
            event = KeywordAlertEvent.objects.create(
                alert=alert,
                keyword=kw.keyword,
                old_rank=kw.previous_rank,
                new_rank=kw.current_rank,
                change=change,
            )
            alert.last_triggered_at = timezone.now()
            alert.save(update_fields=["last_triggered_at"])

            if alert.notification_method == KeywordAlert.METHOD_EMAIL:
                _send_keyword_alert_email(alert, event)

            logger.info(
                f"Keyword alert fired: '{kw.keyword}' moved {abs_change} positions "
                f"({'up' if change > 0 else 'down'}) for website {alert.website_id}"
            )


def _send_keyword_alert_email(alert, event):
    """Send an email notification for a triggered keyword alert."""
    try:
        from django.conf import settings
        from django.core.mail import send_mail

        user = alert.website.user
        direction = "improved" if event.change > 0 else "declined"
        subject = f"Keyword alert: '{event.keyword}' {direction} {abs(event.change)} positions"
        body = (
            f"Hi,\n\n"
            f"Your keyword tracking alert has fired.\n\n"
            f"Keyword: {event.keyword}\n"
            f"Change: {abs(event.change)} positions {direction}\n"
            f"Old rank: #{event.old_rank}\n"
            f"New rank: #{event.new_rank}\n\n"
            f"Log in to your dashboard to see the full report.\n"
        )
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning(f"Failed to send keyword alert email: {e}")


@shared_task(name="apps.analytics.tasks.check_competitor_rankings")
def check_competitor_rankings(competitor_id: str):
    """
    Fetch DataForSEO rankings for a single competitor domain across
    all tracked keywords for its parent website.
    """
    from django.utils import timezone

    from apps.analytics.models import CompetitorDomain, CompetitorKeywordRank, TrackedKeyword
    from apps.analytics.services.dataforseo_service import DataForSEOService

    try:
        comp = CompetitorDomain.objects.select_related("website").get(id=competitor_id)
    except CompetitorDomain.DoesNotExist:
        logger.warning(f"Competitor {competitor_id} not found")
        return

    if not DataForSEOService.is_configured():
        logger.warning("DataForSEO not configured — skipping competitor rank check")
        return

    keywords = list(
        TrackedKeyword.objects.filter(website=comp.website).values_list("keyword", flat=True)
    )
    if not keywords:
        return

    try:
        enriched = DataForSEOService.enrich_keywords(keywords, comp.domain)
        for entry in enriched:
            CompetitorKeywordRank.objects.create(
                competitor=comp,
                keyword=entry["keyword"],
                rank=entry.get("position"),
            )
        comp.last_checked_at = timezone.now()
        comp.save(update_fields=["last_checked_at"])
        logger.info(f"Competitor ranks updated for {comp.domain}: {len(enriched)} keywords")
    except Exception as e:
        logger.error(f"Competitor rank check failed for {comp.domain}: {e}")
