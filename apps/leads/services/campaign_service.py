"""
Email campaign service — create, send, and track campaigns.

Sending strategy:
  1. If Mailchimp is configured for the website → sync via Mailchimp API.
  2. Otherwise → send directly via SendGrid (existing EmailService).
"""
import logging

from django.utils import timezone

from apps.leads.models import EmailCampaign, CampaignRecipient, Lead
from core.exceptions import ResourceNotFound

logger = logging.getLogger("apps")


class CampaignService:
    @staticmethod
    def create(*, website, created_by, subject: str, body: str, segment=None, canva_design_url: str = "") -> EmailCampaign:
        return EmailCampaign.objects.create(
            website=website,
            created_by=created_by,
            subject=subject,
            body=body,
            segment=segment,
            canva_design_url=canva_design_url,
        )

    @staticmethod
    def get(*, website_id: str, campaign_id: int) -> EmailCampaign:
        try:
            return EmailCampaign.objects.get(id=campaign_id, website_id=website_id)
        except EmailCampaign.DoesNotExist:
            raise ResourceNotFound("Campaign not found.")

    @staticmethod
    def list(*, website_id: str):
        return EmailCampaign.objects.filter(website_id=website_id).order_by("-created_at")

    @staticmethod
    def _resolve_leads(campaign: EmailCampaign):
        """Return the queryset of leads for this campaign."""
        qs = Lead.objects.filter(website=campaign.website).exclude(email="")
        if campaign.segment:
            # Basic segment filtering: rules is a dict of field → value filters
            rules = campaign.segment.rules or {}
            if rules.get("min_score"):
                qs = qs.filter(score__gte=rules["min_score"])
            if rules.get("status"):
                qs = qs.filter(status=rules["status"])
        return qs

    @staticmethod
    def send(*, campaign: EmailCampaign, sent_by) -> EmailCampaign:
        """Queue all recipients and send the campaign."""
        if campaign.status not in (EmailCampaign.STATUS_DRAFT, EmailCampaign.STATUS_FAILED):
            raise ValueError(f"Cannot send campaign in status '{campaign.status}'.")

        leads = CampaignService._resolve_leads(campaign)
        if not leads.exists():
            raise ValueError("No leads with email addresses found for this campaign.")

        campaign.status = EmailCampaign.STATUS_SENDING
        campaign.save(update_fields=["status", "updated_at"])

        # Try Mailchimp first
        try:
            from apps.leads.services.mailchimp_service import MailchimpService
            from apps.websites.models import Integration

            integration = Integration.objects.get(
                website=campaign.website, type="mailchimp", is_active=True
            )
            mc_campaign_id = MailchimpService.send_campaign(
                integration=integration,
                campaign=campaign,
                leads=leads,
            )
            campaign.mailchimp_campaign_id = mc_campaign_id
            campaign.status = EmailCampaign.STATUS_SENT
            campaign.sent_at = timezone.now()
            campaign.recipient_count = leads.count()
            campaign.save(update_fields=[
                "mailchimp_campaign_id", "status", "sent_at", "recipient_count", "updated_at"
            ])
            logger.info("Campaign %s sent via Mailchimp (%s)", campaign.id, mc_campaign_id)
            return campaign
        except Integration.DoesNotExist:
            pass
        except Exception as e:
            logger.warning("Mailchimp send failed, falling back to SendGrid: %s", e)

        # Fallback: SendGrid direct send
        return CampaignService._send_via_sendgrid(campaign=campaign, leads=leads)

    @staticmethod
    def _send_via_sendgrid(*, campaign: EmailCampaign, leads) -> EmailCampaign:
        from apps.notifications.services.email_service import EmailService

        sent = 0
        failed = 0

        for lead in leads:
            recipient, _ = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                lead=lead,
                defaults={"status": CampaignRecipient.STATUS_QUEUED},
            )
            success = EmailService.send_email(
                to=lead.email,
                subject=campaign.subject,
                html_content=campaign.body,
            )
            if success:
                recipient.status = CampaignRecipient.STATUS_SENT
                recipient.sent_at = timezone.now()
                sent += 1
            else:
                recipient.status = CampaignRecipient.STATUS_FAILED
                failed += 1
            recipient.save(update_fields=["status", "sent_at"])

        campaign.status = EmailCampaign.STATUS_SENT if sent > 0 else EmailCampaign.STATUS_FAILED
        campaign.sent_at = timezone.now()
        campaign.recipient_count = sent
        campaign.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])

        logger.info("Campaign %s: %d sent, %d failed via SendGrid", campaign.id, sent, failed)
        return campaign

    @staticmethod
    def get_stats(*, campaign: EmailCampaign) -> dict:
        recipients = campaign.recipients.all()
        return {
            "recipient_count": campaign.recipient_count,
            "open_count": campaign.open_count,
            "click_count": campaign.click_count,
            "open_rate": campaign.open_rate,
            "click_rate": campaign.click_rate,
            "sent": recipients.filter(status=CampaignRecipient.STATUS_SENT).count(),
            "opened": recipients.filter(status=CampaignRecipient.STATUS_OPENED).count(),
            "clicked": recipients.filter(status=CampaignRecipient.STATUS_CLICKED).count(),
            "bounced": recipients.filter(status=CampaignRecipient.STATUS_BOUNCED).count(),
            "failed": recipients.filter(status=CampaignRecipient.STATUS_FAILED).count(),
        }

    @staticmethod
    def record_open(*, tracking_id: str) -> None:
        """Record an email open event via tracking pixel."""
        try:
            recipient = CampaignRecipient.objects.select_related("campaign").get(
                tracking_id=tracking_id
            )
            if recipient.status == CampaignRecipient.STATUS_SENT:
                recipient.status = CampaignRecipient.STATUS_OPENED
                recipient.opened_at = timezone.now()
                recipient.save(update_fields=["status", "opened_at"])
                EmailCampaign.objects.filter(pk=recipient.campaign_id).update(
                    open_count=recipient.campaign.open_count + 1
                )
        except CampaignRecipient.DoesNotExist:
            pass

    @staticmethod
    def record_click(*, tracking_id: str) -> None:
        """Record a link click event from a campaign email."""
        try:
            recipient = CampaignRecipient.objects.select_related("campaign").get(
                tracking_id=tracking_id
            )
            if recipient.status in (CampaignRecipient.STATUS_SENT, CampaignRecipient.STATUS_OPENED):
                recipient.status = CampaignRecipient.STATUS_CLICKED
                recipient.clicked_at = timezone.now()
                recipient.save(update_fields=["status", "clicked_at"])
                EmailCampaign.objects.filter(pk=recipient.campaign_id).update(
                    click_count=recipient.campaign.click_count + 1
                )
        except CampaignRecipient.DoesNotExist:
            pass
