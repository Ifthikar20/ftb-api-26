"""
Tracked link service — create short tracked URLs, record clicks, and attribute conversions.
"""
import hashlib
import logging
import secrets

from apps.analytics.models import LinkClick, TrackedLink

logger = logging.getLogger("apps")


class TrackingService:
    @staticmethod
    def _generate_key() -> str:
        """Generate a unique 12-character tracking key."""
        return secrets.token_urlsafe(9)[:12]

    @staticmethod
    def create_link(*, website, destination_url: str, description: str = "", campaign=None) -> TrackedLink:
        """Create a new tracked link."""
        key = TrackingService._generate_key()
        # Ensure uniqueness (collision extremely unlikely but handled)
        while TrackedLink.objects.filter(tracking_key=key).exists():
            key = TrackingService._generate_key()

        return TrackedLink.objects.create(
            website=website,
            destination_url=destination_url,
            tracking_key=key,
            description=description,
            campaign=campaign,
        )

    @staticmethod
    def get_link(tracking_key: str) -> TrackedLink:
        """Look up a tracked link by its key."""
        return TrackedLink.objects.select_related("website", "campaign").get(
            tracking_key=tracking_key
        )

    @staticmethod
    def record_click(
        *,
        tracked_link: TrackedLink,
        ip: str = "",
        user_agent: str = "",
        referrer: str = "",
        tracking_id: str = "",  # CampaignRecipient.tracking_id
    ) -> LinkClick:
        """
        Record a click on a tracked link.

        If tracking_id is provided (from a campaign email link), associate the click
        with the CampaignRecipient for full-funnel attribution.
        """
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64] if ip else ""

        campaign_recipient = None
        if tracking_id:
            try:
                from apps.leads.models import CampaignRecipient
                campaign_recipient = CampaignRecipient.objects.get(tracking_id=tracking_id)
                # Mark the recipient as clicked
                from apps.leads.services.campaign_service import CampaignService
                CampaignService.record_click(tracking_id=str(tracking_id))
            except Exception:
                pass

        click = LinkClick.objects.create(
            tracked_link=tracked_link,
            ip_hash=ip_hash,
            user_agent=user_agent[:500],
            referrer=referrer[:2000],
            campaign_recipient=campaign_recipient,
        )

        TrackedLink.objects.filter(pk=tracked_link.pk).update(
            click_count=tracked_link.click_count + 1
        )

        return click

    @staticmethod
    def record_conversion(*, click: LinkClick) -> None:
        """Mark a click as converted and increment the link's conversion counter."""
        if click.converted:
            return
        LinkClick.objects.filter(pk=click.pk).update(converted=True)
        TrackedLink.objects.filter(pk=click.tracked_link_id).update(
            conversion_count=click.tracked_link.conversion_count + 1
        )

    @staticmethod
    def get_click_stats(*, tracked_link: TrackedLink) -> dict:
        clicks = tracked_link.clicks.all()
        return {
            "total_clicks": tracked_link.click_count,
            "conversions": tracked_link.conversion_count,
            "conversion_rate": round(
                tracked_link.conversion_count / tracked_link.click_count * 100, 1
            ) if tracked_link.click_count else 0.0,
            "unique_ips": clicks.values("ip_hash").distinct().count(),
        }
