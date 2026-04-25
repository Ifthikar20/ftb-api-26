"""
Resend email sending service — secure, developer-friendly email API.

Why Resend:
  - Per-domain isolation: each business gets its own verified domain
  - Built-in marketing: Broadcasts API + Audiences
  - Batch sending: up to 100 emails per API call
  - Auto DKIM/SPF/DMARC per domain

Pricing: ~$20/mo for 50k emails (Pro plan).

Requires:
  - RESEND_API_KEY in settings/env
  - Verified sending domain in Resend dashboard
"""

import logging

from django.conf import settings

logger = logging.getLogger("apps")

# Max emails per batch API call (Resend limit)
BATCH_SIZE = 100


def resend_configured() -> bool:
    """Return True if Resend API key is available."""
    key = getattr(settings, "RESEND_API_KEY", "")
    return bool(key)


class ResendService:
    """Send emails via Resend API."""

    @staticmethod
    def _init():
        """Initialize the resend SDK with the API key."""
        import resend

        resend.api_key = getattr(settings, "RESEND_API_KEY", "")
        return resend

    @staticmethod
    def send_email(
        *, to: str, subject: str, html_content: str,
        from_name: str = "", from_email: str = "",
    ) -> bool:
        """Send a single email via Resend. Returns True on success."""
        try:
            resend = ResendService._init()

            sender = from_email or getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@fetchbot.ai"
            )
            if from_name:
                sender = f"{from_name} <{sender}>"

            resend.Emails.send({
                "from": sender,
                "to": [to],
                "subject": subject,
                "html": html_content,
            })
            return True
        except Exception as e:
            logger.error("Resend send failed to %s: %s", to, e)
            return False

    @staticmethod
    def send_bulk(*, campaign, leads, variant_map: dict) -> dict:
        """Send a campaign to multiple leads via Resend Batch API.

        Sends in batches of 100 (Resend's per-request limit).
        Returns {sent: int, failed: int}.
        """
        from django.utils import timezone
        from apps.leads.models import CampaignRecipient

        resend = ResendService._init()

        sender_email = campaign.from_email or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@fetchbot.ai"
        )
        sender = (
            f"{campaign.from_name} <{sender_email}>"
            if campaign.from_name
            else sender_email
        )

        sent = 0
        failed = 0

        # Build recipient objects and email payloads
        lead_list = list(leads)
        batch = []
        batch_leads = []

        for lead in lead_list:
            variant = variant_map.get(lead.pk, CampaignRecipient.VARIANT_A)
            subject = (
                campaign.subject
                if variant == CampaignRecipient.VARIANT_A
                else (campaign.subject_b or campaign.subject)
            )
            body = (
                campaign.body
                if variant == CampaignRecipient.VARIANT_A
                else (campaign.body_b or campaign.body)
            )

            # Ensure recipient record exists
            recipient, _ = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                lead=lead,
                defaults={
                    "status": CampaignRecipient.STATUS_QUEUED,
                    "variant": variant,
                },
            )

            batch.append({
                "from": sender,
                "to": [lead.email],
                "subject": subject,
                "html": body,
            })
            batch_leads.append((lead, recipient, variant))

            # Flush batch when it hits the limit
            if len(batch) >= BATCH_SIZE:
                _sent, _failed = ResendService._flush_batch(
                    resend, batch, batch_leads, timezone
                )
                sent += _sent
                failed += _failed
                batch = []
                batch_leads = []

        # Flush remaining
        if batch:
            _sent, _failed = ResendService._flush_batch(
                resend, batch, batch_leads, timezone
            )
            sent += _sent
            failed += _failed

        return {"sent": sent, "failed": failed}

    @staticmethod
    def _flush_batch(resend, batch, batch_leads, timezone):
        """Send a single batch of up to 100 emails."""
        sent = 0
        failed = 0
        try:
            result = resend.Batch.send(batch)
            # result.data is a list of {id: "..."} for each sent email
            now = timezone.now()
            for i, (lead, recipient, variant) in enumerate(batch_leads):
                # Resend batch processes each email independently
                # If we got here without exception, assume success
                recipient.status = recipient.STATUS_SENT
                recipient.sent_at = now
                recipient.save(update_fields=["status", "sent_at", "variant"])
                sent += 1

            logger.info("Resend batch: %d emails sent successfully", len(batch))

        except Exception as e:
            logger.error("Resend batch send failed: %s", e)
            # Mark all in this batch as failed
            for lead, recipient, variant in batch_leads:
                recipient.status = recipient.STATUS_FAILED
                recipient.save(update_fields=["status", "variant"])
                failed += 1

        return sent, failed
