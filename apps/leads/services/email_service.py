"""
Lead email service — send emails to leads and log them.
"""
import logging

from django.core.mail import send_mail
from django.conf import settings

from apps.leads.models import Lead, LeadEmail

logger = logging.getLogger(__name__)


class LeadEmailService:
    @staticmethod
    def send_email(*, lead_id: int, subject: str, body: str, sent_by) -> LeadEmail:
        """Send an email to a lead and record it."""
        lead = Lead.objects.select_related("visitor").get(pk=lead_id)
        to_email = lead.email

        if not to_email:
            raise ValueError("Lead has no email address.")

        # Send via Django's configured email backend
        status = "sent"
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            status = "failed"

        # Log the email
        email_record = LeadEmail.objects.create(
            lead=lead,
            sent_by=sent_by,
            subject=subject,
            body=body,
            to_email=to_email,
            status=status,
        )

        return email_record

    @staticmethod
    def get_email_history(*, lead_id: int) -> list:
        """Return all emails sent to a lead."""
        return list(
            LeadEmail.objects.filter(lead_id=lead_id)
            .values("id", "subject", "to_email", "status", "sent_at", "body")
            .order_by("-sent_at")
        )
