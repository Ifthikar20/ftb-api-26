import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.notifications.tasks.send_weekly_reports")
def send_weekly_reports():
    """Send weekly summary reports to all users."""
    from apps.accounts.models import User
    from apps.notifications.services.email_service import EmailService

    for user in User.objects.filter(is_active=True):
        try:
            EmailService.send_email(
                to=user.email,
                subject="Your GrowthPilot Weekly Report",
                html_content=f"<p>Hi {user.first_name}, here is your weekly growth summary.</p>",
            )
        except Exception as e:
            logger.error(f"Weekly report failed for {user.email}: {e}")
