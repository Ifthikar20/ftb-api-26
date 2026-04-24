"""
AWS SES email sending service — lowest-cost transactional email option.

Pricing: ~$0.10 per 1,000 emails.

Requires:
  - AWS_SES_ACCESS_KEY_ID  (or falls back to AWS_ACCESS_KEY_ID)
  - AWS_SES_SECRET_ACCESS_KEY  (or falls back to AWS_SECRET_ACCESS_KEY)
  - AWS_SES_REGION  (default: us-east-1)
  - Verified domain/sender identity in SES console
"""

import logging

from django.conf import settings

logger = logging.getLogger("apps")


def ses_configured() -> bool:
    """Return True if AWS SES credentials are available."""
    key = getattr(settings, "AWS_SES_ACCESS_KEY_ID", "") or getattr(settings, "AWS_ACCESS_KEY_ID", "")
    secret = getattr(settings, "AWS_SES_SECRET_ACCESS_KEY", "") or getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
    return bool(key and secret)


class SESService:
    """Send emails via AWS SES using boto3."""

    @staticmethod
    def _get_client():
        import boto3

        key = getattr(settings, "AWS_SES_ACCESS_KEY_ID", "") or getattr(settings, "AWS_ACCESS_KEY_ID", "")
        secret = getattr(settings, "AWS_SES_SECRET_ACCESS_KEY", "") or getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
        region = getattr(settings, "AWS_SES_REGION", "us-east-1")

        return boto3.client(
            "ses",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=region,
        )

    @staticmethod
    def send_email(*, to: str, subject: str, html_content: str,
                   from_name: str = "", from_email: str = "") -> bool:
        """Send a single email via SES. Returns True on success."""
        try:
            client = SESService._get_client()
            sender = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@fetchbot.ai")
            if from_name:
                sender = f"{from_name} <{sender}>"

            client.send_email(
                Source=sender,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                    },
                },
            )
            return True
        except Exception as e:
            logger.error("SES send failed to %s: %s", to, e)
            return False

    @staticmethod
    def send_bulk(*, campaign, leads, variant_map: dict) -> dict:
        """Send a campaign to multiple leads via SES.

        Returns {sent: int, failed: int}.
        """
        from django.utils import timezone
        from apps.leads.models import CampaignRecipient

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

            success = SESService.send_email(
                to=lead.email,
                subject=subject,
                html_content=body,
                from_name=campaign.from_name,
                from_email=campaign.from_email,
            )

            if success:
                recipient.status = CampaignRecipient.STATUS_SENT
                recipient.sent_at = timezone.now()
                sent += 1
            else:
                recipient.status = CampaignRecipient.STATUS_FAILED
                failed += 1
            recipient.save(update_fields=["status", "sent_at", "variant"])

        return {"sent": sent, "failed": failed}
