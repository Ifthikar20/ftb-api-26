from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserProfileSerializer,
    VerifyEmailSerializer,
)
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.oauth_service import OAuthService
from apps.accounts.services.user_service import UserService
from core.interceptors.throttling import AuthRateThrottle, PasswordResetThrottle

REFRESH_COOKIE_SETTINGS = {
    "key": "refresh_token",
    "httponly": True,
    "secure": True,
    "samesite": "None",
    "max_age": 7 * 24 * 60 * 60,
    "path": "/",
}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        # Beta gate: when SIGNUPS_ENABLED is False, refuse new accounts at the
        # API layer too so the closed signup can't be bypassed by anyone hitting
        # the endpoint directly.
        from django.conf import settings as dj_settings

        if not getattr(dj_settings, "SIGNUPS_ENABLED", True):
            return Response(
                {
                    "error": {
                        "code": "signups_closed",
                        "message": (
                            "FetchBot is in private beta. New sign-ups are paused — "
                            "please contact us for access."
                        ),
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService.register(**serializer.validated_data)

        from apps.accounts.tasks import send_verification_email
        send_verification_email.delay(str(user.id))

        return Response(
            {"message": "Account created. Please check your email to verify."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AuthService.login(
            **serializer.validated_data,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            request=request,
        )

        response = Response(
            {"access": result["access"], "user": result["user"]},
            status=status.HTTP_200_OK,
        )
        response.set_cookie(value=result["refresh"], **REFRESH_COOKIE_SETTINGS)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        AuthService.logout(refresh_token=refresh_token, user=request.user)

        response = Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie("refresh_token", path="/")
        return response


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = []  # No throttling — called on every page load for session restore

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "No refresh token provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        result = AuthService.refresh_token(refresh_token=refresh_token)

        response = Response({"access": result["access"]}, status=status.HTTP_200_OK)
        response.set_cookie(value=result["refresh"], **REFRESH_COOKIE_SETTINGS)
        return response


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.verify_email_otp(**serializer.validated_data)
        return Response({"message": "Email verified successfully."})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        email = request.data.get("email", "")
        from apps.accounts.models import User
        try:
            user = User.objects.get(email__iexact=email, is_email_verified=False)
            from apps.accounts.tasks import send_verification_email
            send_verification_email.delay(str(user.id))
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists
        return Response({"message": "If an unverified account exists, a new code has been sent."})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = AuthService.generate_password_reset_token(email=serializer.validated_data["email"])
        if token:
            from apps.accounts.tasks import send_password_reset_email
            send_password_reset_email.delay(serializer.validated_data["email"], token)
        return Response({"message": "If an account exists with that email, a reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(**serializer.validated_data)
        return Response({"message": "Password reset successfully."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.change_password(user=request.user, **serializer.validated_data)
        return Response({"message": "Password changed successfully."})


class GoogleOAuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri", "")
        if not code:
            return Response({"error": "Authorization code required."}, status=status.HTTP_400_BAD_REQUEST)

        user = OAuthService.google_authenticate(code=code, redirect_uri=redirect_uri)
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "access": str(refresh.access_token),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "plan": user.plan,
                    "onboarding_complete": user.onboarding_complete,
                },
            }
        )
        response.set_cookie(value=str(refresh), **REFRESH_COOKIE_SETTINGS)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    patch = put

    def delete(self, request):
        UserService.delete_account(user=request.user)
        return Response({"message": "Account deleted."}, status=status.HTTP_200_OK)


class MeExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = UserService.export_data(user=request.user)
        return Response(data)


class SessionView(APIView):
    """
    Post-login bootstrap. Returns the minimum the frontend needs to decide
    where to route the user: onboarding, paywall, or app.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.websites.models import Website
        from core.utils.constants import SubscriptionStatus

        user = request.user

        websites = list(Website.objects.filter(user=user, is_active=True).only(
            "id", "name", "url", "onboarding_completed"
        ))
        needs_onboarding = not websites or any(not w.onboarding_completed for w in websites)
        incomplete = next((w for w in websites if not w.onboarding_completed), None)

        sub = getattr(user, "subscription", None)
        if sub is None:
            is_paying = False
        elif sub.status == SubscriptionStatus.ACTIVE:
            is_paying = True
        elif sub.status == SubscriptionStatus.TRIALING and sub.stripe_subscription_id:
            is_paying = True
        else:
            is_paying = False

        if needs_onboarding:
            next_route = "onboarding"
        elif not is_paying:
            next_route = "paywall"
        else:
            next_route = "app"

        return Response({
            "user": UserProfileSerializer(user).data,
            "onboarding": {
                "needs_onboarding": needs_onboarding,
                "first_incomplete_website_id": str(incomplete.id) if incomplete else None,
                "websites_count": len(websites),
            },
            "subscription": {
                "status": sub.status if sub else None,
                "plan": sub.plan if sub else None,
                "is_paying": is_paying,
            },
            "next_route": next_route,
        })


class AIUsageView(APIView):
    """
    Centralised AI usage rollup for the authenticated user.

    One source of truth for the Settings "Overall Usage" panel — every AI
    call site (Lead Finder, Messaging, Analytics, LLM Ranking upstream +
    extraction, Competitor Discovery) writes through core.ai_tracking and
    rolls up here, broken down by module, model, provider, and role.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.ai_tracking import get_usage_summary

        days = int(request.query_params.get("days", 30))
        days = min(days, 365)  # cap at 1 year
        summary = get_usage_summary(user=request.user, days=days)

        # Serialise dates and Decimals for JSON
        for d in summary.get("daily", []):
            d["day"] = d["day"].isoformat() if d.get("day") else None
            d["cost"] = float(d.get("cost") or 0)
        for m in summary.get("by_module", []):
            m["cost"] = float(m.get("cost") or 0)
        for m in summary.get("by_model", []):
            m["cost"] = float(m.get("cost") or 0)
        for p in summary.get("by_provider", []):
            p["cost"] = float(p.get("cost") or 0)

        return Response(summary)

