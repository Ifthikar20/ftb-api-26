import logging
from django.conf import settings

logger = logging.getLogger("apps")


class EmailService:
    @staticmethod
    def send_email(*, to: str, subject: str, html_content: str) -> bool:
        """Send email via SendGrid."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content

            sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
            mail = Mail(
                from_email=Email("noreply@growthpilot.io"),
                to_emails=To(to),
                subject=subject,
                html_content=Content("text/html", html_content),
            )
            response = sg.client.mail.send.post(request_body=mail.get())
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error(f"Email send failed to {to}: {e}")
            return False

    @staticmethod
    def send_hot_lead_alert(*, user, lead) -> None:
        from apps.notifications.models import NotificationPreference
        try:
            prefs = user.notification_preferences
            if not prefs.hot_lead_email:
                return
        except NotificationPreference.DoesNotExist:
            return

        EmailService.send_email(
            to=user.email,
            subject=f"🔥 Hot lead detected — Score {lead.score}",
            html_content=f"<p>A new hot lead with score {lead.score} was detected on your website.</p>",
        )
