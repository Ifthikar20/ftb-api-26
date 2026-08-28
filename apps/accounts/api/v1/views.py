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


# Cookie attributes for the JWT refresh token.
#
# SameSite=Lax is the CSRF control for this cookie, and it is the only
# one. The refresh/logout endpoints authenticate from the cookie alone,
# so with SameSite=None any origin could make a browser POST to them
# with the victim's credentials attached: forced logout, refresh-token
# churn against ROTATE_REFRESH_TOKENS, and login-CSRF that silently
# drops a victim into an attacker-controlled account. Lax stops the
# browser attaching the cookie to cross-site POSTs at all, which
# removes the precondition rather than mitigating the consequence.
#
# Nothing in production needs cross-site delivery: nginx.prod.conf
# serves the SPA (location /) and the API (location /api/) from the
# same cansee.ai server block, so every request that matters is
# same-origin. The earlier SameSite=None dated from a topology that no
# longer exists.
#
# Note SameSite keys on the registrable domain, not the full host, so
# splitting to app.cansee.ai + api.cansee.ai stays same-site and
# keeps working. Lax also still sends the cookie on top-level GET
# navigations, so the Google Search Console OAuth callback is fine.
#
# Only a genuinely different registrable domain (a *.vercel.app preview,
# say) would force SameSite=None. If that ever happens, do NOT just flip
# this value: SameSite=None reopens the CSRF hole above, so it has to
# come with csrf_protect on the three cookie-reading endpoints, an
# ensure_csrf_cookie bootstrap route, X-CSRFToken on the SPA client, and
# the new origin added to CSRF_TRUSTED_ORIGINS.
#
# Dev (DEBUG=True) additionally relaxes Secure: browsers grant a
# localhost exemption, but Vite's proxy over http makes delivery flaky,
# which kicks developers to /login.
def _refresh_cookie_settings():
    """Cookie kwargs for the refresh token, resolved per call.

    ``secure`` follows ``SESSION_COOKIE_SECURE``, which base.py derives from
    PUBLIC_SCHEME -- so this cookie can never disagree with the session and
    CSRF cookies about whether the deployment is on TLS. That matters
    because a Secure cookie is silently discarded by the browser over
    http://: on a plaintext deployment, login would return 200 and the
    session would then die on the first reload, with nothing in the logs.

    DEBUG still forces it off regardless: Vite proxies over http locally, so
    Secure would drop the cookie and bounce developers to /login.

    This is deliberately NOT cached in a module-level constant. It used to
    be, which froze the value at import time under whatever DEBUG was then
    and made it unreachable by settings -- see TestRefreshCookieBinding.
    """
    from django.conf import settings as _settings

    secure = bool(getattr(_settings, "SESSION_COOKIE_SECURE", True))
    if getattr(_settings, "DEBUG", False):
        secure = False

    return {
        "key": "refresh_token",
        "httponly": True,
        "secure": secure,
        "samesite": "Lax",
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
                            "Cansee is in private beta. New sign-ups are paused — "
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
        response.set_cookie(value=result["refresh"], **_refresh_cookie_settings())
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
        response.set_cookie(value=result["refresh"], **_refresh_cookie_settings())
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
        response.set_cookie(value=str(refresh), **_refresh_cookie_settings())
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
        from django.conf import settings

        from apps.billing.services import polar_billing
        from apps.billing.services.plan_limits import subscription_state
        from apps.websites.models import Website

        user = request.user

        websites = list(Website.objects.filter(user=user, is_active=True).only(
            "id", "name", "url"
        ))
        needs_onboarding = not websites

        sub = getattr(user, "subscription", None)
        # A trial whose end date passed without a conversion webhook
        # (dev has none; prod can lag) is settled against Polar here,
        # cooldown-limited, so the row below is the real state.
        sub = polar_billing.reverify_ended_trial(user, sub)
        # One builder for the whole subscription block so every surface
        # labels a trial, a paid plan and a lapsed row the same way.
        subscription = subscription_state(sub)
        is_paying = subscription["is_paying"]

        # Onboarding first, then paywall. We want users to see the
        # value (their topics, competitors, tracked brands) before
        # they're asked to pay — invested users convert better. So
        # the funnel is: register -> onboarding modal -> paywall ->
        # dashboard.
        # The paywall step is skipped entirely while PAYWALL_ENABLED is
        # False (the flag lives in settings and is env-driven, so it can
        # be flipped back on without a code change), and permanently for
        # users who chose the Free plan from the paywall once
        # (paywall_dismissed_at set via POST /billing/paywall/dismiss/).
        if needs_onboarding:
            next_route = "onboarding"
        elif (
            not is_paying
            and settings.PAYWALL_ENABLED
            and user.paywall_dismissed_at is None
        ):
            next_route = "paywall"
        else:
            next_route = "app"

        return Response({
            "user": UserProfileSerializer(user).data,
            "onboarding": {
                "needs_onboarding": needs_onboarding,
                "websites_count": len(websites),
            },
            "subscription": subscription,
            "paywall_dismissed": user.paywall_dismissed_at is not None,
            "next_route": next_route,
        })


class AIUsageView(APIView):
    """
    Centralised AI usage rollup for the authenticated user.

    One source of truth for the Settings "Overall Usage" panel — every AI
    call site writes through core.ai_tracking and rolls up here, broken
    down by module, model, provider, and role.

    The window is always the CURRENT BILLING PERIOD (subscription cycle
    when one exists, calendar month otherwise) — the same window the
    spend wall and cap notifications use, so the page can never disagree
    with enforcement. Totals come from Polar meters once
    POLAR_READS_ENABLED is on, with automatic fallback to the local
    ledger. A legacy ``days`` query param is accepted and ignored.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.metering.services.usage_reader import get_period_usage

        return Response(get_period_usage(request.user))

