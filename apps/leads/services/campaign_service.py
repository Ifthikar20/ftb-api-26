"""
Email campaign service — create, send, and track campaigns.

Sending priority:
  1. AWS SES (cheapest — ~$0.10/1k emails)
  2. Mailchimp (if integration active)
  3. SendGrid (fallback)

A/B testing:
  When is_ab_test=True, recipients are randomly split between
  variant A (subject/body) and variant B (subject_b/body_b).
"""
import logging
import random

from django.utils import timezone

from apps.leads.models import CampaignRecipient, EmailCampaign, Lead
from core.exceptions import ResourceNotFound

logger = logging.getLogger("apps")


class CampaignService:
    @staticmethod
    def create(
        *, website, created_by, subject: str, body: str,
        name: str = "", from_name: str = "", from_email: str = "",
        segment=None, canva_design_url: str = "",
        is_ab_test: bool = False, subject_b: str = "", body_b: str = "",
        ab_split_ratio: int = 50,
    ) -> EmailCampaign:
        return EmailCampaign.objects.create(
            website=website,
            created_by=created_by,
            name=name,
            subject=subject,
            body=body,
            from_name=from_name,
            from_email=from_email,
            segment=segment,
            canva_design_url=canva_design_url,
            is_ab_test=is_ab_test,
            subject_b=subject_b,
            body_b=body_b,
            ab_split_ratio=ab_split_ratio,
        )

    @staticmethod
    def get(*, website_id: str, campaign_id: int) -> EmailCampaign:
        try:
            return EmailCampaign.objects.get(id=campaign_id, website_id=website_id)
        except EmailCampaign.DoesNotExist:
            raise ResourceNotFound("Campaign not found.") from None

    @staticmethod
    def list(*, website_id: str):
        return EmailCampaign.objects.filter(website_id=website_id).order_by("-created_at")

    @staticmethod
    def preview_recipients(*, website_id: str, segment_id=None) -> int:
        """Return the count of leads that would receive the campaign."""
        qs = Lead.objects.filter(website_id=website_id).exclude(email="")
        if segment_id:
            from apps.leads.models import LeadSegment
            try:
                segment = LeadSegment.objects.get(id=segment_id, website_id=website_id)
                rules = segment.rules or {}
                if rules.get("min_score"):
                    qs = qs.filter(score__gte=rules["min_score"])
                if rules.get("status"):
                    qs = qs.filter(status=rules["status"])
            except LeadSegment.DoesNotExist:
                pass
        return qs.count()

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
    def _build_variant_map(campaign, lead_list):
        """Assign A/B variants to leads."""
        if campaign.is_ab_test and campaign.subject_b:
            random.shuffle(lead_list)
            split_point = int(len(lead_list) * campaign.ab_split_ratio / 100)
            return {
                lead.pk: CampaignRecipient.VARIANT_A if i < split_point else CampaignRecipient.VARIANT_B
                for i, lead in enumerate(lead_list)
            }
        return {lead.pk: CampaignRecipient.VARIANT_A for lead in lead_list}

    @staticmethod
    def send(*, campaign: EmailCampaign, sent_by) -> EmailCampaign:
        """Queue all recipients and send the campaign.

        Priority: SES → Mailchimp → SendGrid
        """
        if campaign.status not in (EmailCampaign.STATUS_DRAFT, EmailCampaign.STATUS_FAILED):
            raise ValueError(f"Cannot send campaign in status '{campaign.status}'.")

        leads = CampaignService._resolve_leads(campaign)
        if not leads.exists():
            raise ValueError("No leads with email addresses found for this campaign.")

        campaign.status = EmailCampaign.STATUS_SENDING
        campaign.save(update_fields=["status", "updated_at"])

        lead_list = list(leads)
        variant_map = CampaignService._build_variant_map(campaign, lead_list)

        # ── Strategy 1: Resend (recommended — per-domain isolation, batch API) ──
        try:
            from apps.leads.services.resend_service import ResendService, resend_configured
            if resend_configured():
                result = ResendService.send_bulk(campaign=campaign, leads=lead_list, variant_map=variant_map)
                campaign.status = EmailCampaign.STATUS_SENT if result["sent"] > 0 else EmailCampaign.STATUS_FAILED
                campaign.sent_at = timezone.now()
                campaign.recipient_count = result["sent"]
                campaign.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])
                logger.info("Campaign %s: %d sent, %d failed via Resend", campaign.id, result["sent"], result["failed"])
                return campaign
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Resend send failed, falling back: %s", e)

        # ── Strategy 2: AWS SES (cheapest raw cost) ──
        try:
            from apps.leads.services.ses_service import SESService, ses_configured
            if ses_configured():
                result = SESService.send_bulk(campaign=campaign, leads=lead_list, variant_map=variant_map)
                campaign.status = EmailCampaign.STATUS_SENT if result["sent"] > 0 else EmailCampaign.STATUS_FAILED
                campaign.sent_at = timezone.now()
                campaign.recipient_count = result["sent"]
                campaign.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])
                logger.info("Campaign %s: %d sent, %d failed via SES", campaign.id, result["sent"], result["failed"])
                return campaign
        except ImportError:
            pass
        except Exception as e:
            logger.warning("SES send failed, falling back: %s", e)

        # ── Strategy 3: Mailchimp ──
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

        # ── Strategy 4: SendGrid (last resort) ──
        return CampaignService._send_via_sendgrid(campaign=campaign, leads=lead_list, variant_map=variant_map)

    @staticmethod
    def _send_via_sendgrid(*, campaign: EmailCampaign, leads, variant_map: dict) -> EmailCampaign:
        from apps.notifications.services.email_service import EmailService

        sent = 0
        failed = 0

        for lead in leads:
            variant = variant_map.get(lead.pk, CampaignRecipient.VARIANT_A)
            subject = campaign.subject if variant == CampaignRecipient.VARIANT_A else (campaign.subject_b or campaign.subject)
            body = campaign.body if variant == CampaignRecipient.VARIANT_A else (campaign.body_b or campaign.body)

            recipient, _ = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                lead=lead,
                defaults={"status": CampaignRecipient.STATUS_QUEUED, "variant": variant},
            )
            success = EmailService.send_email(
                to=lead.email,
                subject=subject,
                html_content=body,
            )
            if success:
                recipient.status = CampaignRecipient.STATUS_SENT
                recipient.sent_at = timezone.now()
                sent += 1
            else:
                recipient.status = CampaignRecipient.STATUS_FAILED
                failed += 1
            recipient.save(update_fields=["status", "sent_at", "variant"])

        campaign.status = EmailCampaign.STATUS_SENT if sent > 0 else EmailCampaign.STATUS_FAILED
        campaign.sent_at = timezone.now()
        campaign.recipient_count = sent
        campaign.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])

        logger.info("Campaign %s: %d sent, %d failed via SendGrid", campaign.id, sent, failed)
        return campaign

    @staticmethod
    def get_stats(*, campaign: EmailCampaign) -> dict:
        recipients = campaign.recipients.all()
        stats = {
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

        # A/B testing breakdown
        if campaign.is_ab_test:
            for variant in (CampaignRecipient.VARIANT_A, CampaignRecipient.VARIANT_B):
                v_recipients = recipients.filter(variant=variant)
                v_total = v_recipients.count() or 1
                v_opened = v_recipients.filter(
                    status__in=[CampaignRecipient.STATUS_OPENED, CampaignRecipient.STATUS_CLICKED]
                ).count()
                v_clicked = v_recipients.filter(status=CampaignRecipient.STATUS_CLICKED).count()
                stats[f"variant_{variant.lower()}"] = {
                    "recipients": v_recipients.count(),
                    "opened": v_opened,
                    "clicked": v_clicked,
                    "open_rate": round(v_opened / v_total * 100, 1),
                    "click_rate": round(v_clicked / v_total * 100, 1),
                }

        return stats

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

    @staticmethod
    def generate_email_body(*, prompt: str, website_name: str = "") -> str:
        """Generate email body HTML using Claude AI."""
        try:
            import anthropic
        except ImportError:
            return ""

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not api_key:
            return ""

        try:
            from django.conf import settings as django_settings
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                system=(
                    "You are an expert email copywriter. Generate a professional, engaging email body "
                    "in HTML format. Use clean, inline-styled HTML suitable for email clients. "
                    "Include a clear call-to-action. Keep it concise (3-5 paragraphs max). "
                    f"The sender is: {website_name or 'a business'}. "
                    "Return ONLY the HTML — no markdown, no explanation."
                ),
                messages=[{"role": "user", "content": prompt}],
            )

            # Track usage
            try:
                from core.ai_tracking import record_usage
                record_usage(
                    module="campaigns",
                    model_name="claude-sonnet-4-20250514",
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
            except Exception:
                pass

            return response.content[0].text
        except Exception as e:
            logger.error("AI email generation failed: %s", e)
            return ""
