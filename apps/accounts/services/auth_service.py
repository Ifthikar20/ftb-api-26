import logging
import secrets
import string
from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    EmailVerificationOTP,
    LoginAttempt,
    PasswordResetToken,
    User,
)
from core.logging.audit_logger import audit_log

security_logger = logging.getLogger("security")


class AuthService:
    """
    Handles all authentication business logic.
    Views are thin — they call this service and return responses.
    """

    @staticmethod
    def register(
        *, email: str, password: str, full_name: str, company_name: str = ""
    ) -> User:
        """Create a new user account with email verification pending."""
        if User.objects.filter(email__iexact=email).exists():
            raise ValueError("An account with this email already exists.")

        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            company_name=company_name,
            is_email_verified=False,
        )

        audit_log("user.registered", user=user, metadata={"method": "email"})
        return user

    @staticmethod
    def login(
        *, email: str, password: str, ip_address: str, user_agent: str, request=None
    ) -> dict:
        """Authenticate user and return JWT token pair."""
        user = authenticate(request=request, email=email, password=password)

        if user is None:
            LoginAttempt.objects.create(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
            )
            security_logger.warning(
                "Failed login attempt",
                extra={"email": email, "ip": ip_address},
            )
            raise ValueError("Invalid email or password.")

        if not user.is_email_verified:
            raise ValueError("Please verify your email before logging in.")

        if not user.is_active:
            security_logger.warning(
                "Login attempt on deactivated account",
                extra={"user_id": str(user.id), "ip": ip_address},
            )
            raise ValueError("This account has been deactivated.")

        LoginAttempt.objects.create(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            user=user,
        )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)
        audit_log("user.login", user=user, metadata={"ip": ip_address})

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "plan": user.plan,
                "onboarding_complete": user.onboarding_complete,
            },
        }

    @staticmethod
    def logout(*, refresh_token: str, user: User) -> None:
        """Blacklist the refresh token to invalidate the session."""
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            audit_log("user.logout", user=user)
        except Exception:
            pass

    @staticmethod
    def refresh_token(*, refresh_token: str) -> dict:
        """Issue new access token from valid refresh token."""
        try:
            refresh = RefreshToken(refresh_token)
            return {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        except Exception:
            raise ValueError("Refresh token is invalid or expired.") from None

    @staticmethod
    def generate_email_otp(*, user: User) -> str:
        """Generate a 6-digit OTP for email verification."""
        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        expires_at = timezone.now() + timedelta(minutes=15)
        EmailVerificationOTP.objects.create(
            user=user, otp=otp, expires_at=expires_at
        )
        return otp

    @staticmethod
    def verify_email_otp(*, email: str, otp: str) -> User:
        """Verify the OTP and mark the user's email as verified."""
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValueError("Invalid OTP.") from None

        verification = (
            EmailVerificationOTP.objects.filter(
                user=user,
                otp=otp,
                used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not verification:
            raise ValueError("Invalid or expired OTP.")

        verification.used = True
        verification.save(update_fields=["used"])

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        audit_log("user.email_verified", user=user)
        return user

    @staticmethod
    def generate_password_reset_token(*, email: str) -> str:
        """Generate a secure password reset token."""
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Don't reveal whether the email exists
            return ""

        token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timedelta(hours=1)
        PasswordResetToken.objects.create(user=user, token=token, expires_at=expires_at)
        return token

    @staticmethod
    def reset_password(*, token: str, new_password: str) -> User:
        """Reset password using a valid reset token."""
        try:
            reset_token = PasswordResetToken.objects.get(
                token=token, used=False, expires_at__gt=timezone.now()
            )
        except PasswordResetToken.DoesNotExist:
            raise ValueError("Invalid or expired reset token.") from None

        user = reset_token.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        reset_token.used = True
        reset_token.save(update_fields=["used"])

        audit_log("user.password_reset", user=user)
        return user

    @staticmethod
    def change_password(*, user: User, old_password: str, new_password: str) -> None:
        """Change password for an authenticated user."""
        if not user.check_password(old_password):
            raise ValueError("Current password is incorrect.")
        user.set_password(new_password)
        user.save(update_fields=["password"])
        audit_log("user.password_changed", user=user)
