import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.accounts.tasks.send_verification_email")
def send_verification_email(user_id: str):
    """Send email verification OTP to user."""
    from apps.accounts.models import User
    from apps.accounts.services.auth_service import AuthService

    try:
        user = User.objects.get(id=user_id)
        otp = AuthService.generate_email_otp(user=user)
        logger.info(f"Verification OTP for {user.email}: {otp}")
        # TODO: Send actual email via SendGrid
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for verification email.")


@shared_task(name="apps.accounts.tasks.send_password_reset_email")
def send_password_reset_email(email: str, token: str):
    """Send password reset email."""
    logger.info(f"Password reset token for {email}: {token}")
    # TODO: Send actual email via SendGrid


@shared_task(name="apps.accounts.tasks.expire_inactive_sessions")
def expire_inactive_sessions():
    """Clean up expired sessions."""
    from django.contrib.sessions.backends.db import SessionStore
    logger.info("Session expiry task completed.")
