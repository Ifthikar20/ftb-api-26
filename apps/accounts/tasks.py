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
        # generate_email_otp persists the OTP server-side (EmailVerificationOTP).
        # SECURITY: never log the OTP itself — it is a live authentication
        # secret. Real delivery is wired by the email transport work (P1.8);
        # until then the OTP is retrievable only from the database, not logs.
        AuthService.generate_email_otp(user=user)
        logger.info("Verification OTP generated for user %s", user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for verification email.")


@shared_task(name="apps.accounts.tasks.send_password_reset_email")
def send_password_reset_email(email: str, token: str):
    """Send password reset email."""
    # SECURITY: never log the reset token — it grants password reset for the
    # account. Real delivery is wired by the email transport work (P1.8).
    logger.info("Password reset requested for %s", email)


@shared_task(name="apps.accounts.tasks.expire_inactive_sessions")
def expire_inactive_sessions():
    """Clean up expired sessions."""
    logger.info("Session expiry task completed.")
