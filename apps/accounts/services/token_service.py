"""Single factory for issuing and rotating JWT session pairs.

Every login path — password, Google, invitation accept, future IdP lanes —
funnels through ``issue_session`` so the checks (is_active,
is_email_verified), the LoginAttempt audit row, and the custom claims are
identical no matter how the user authenticated. Before this existed the
Google path minted tokens inline and skipped all three.

Claims added to the refresh token (SimpleJWT copies them onto every access
token derived from it):

- ``org_id`` / ``org_role`` — the user's organization membership at issue
  time. Convenience only: authorization always re-checks the DB. Refreshed
  on every rotation so role changes propagate at refresh cadence.
- ``amr`` — how this session authenticated (["pwd"], ["google"], ...),
  so an SSO-enforcement sweep can tell password sessions from IdP ones.
"""
import logging

from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import LoginAttempt, User
from core.logging.audit_logger import audit_log

security_logger = logging.getLogger("security")


def _org_claims(user) -> dict:
    """Resolve the user's org membership to token claims. {} when org-less."""
    membership = (
        user.org_memberships.select_related("organization")
        .order_by("created_at")
        .first()
    )
    if not membership:
        return {}
    return {
        "org_id": str(membership.organization_id),
        "org_role": membership.role,
    }


def _user_payload(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "plan": user.plan,
        "onboarding_complete": user.onboarding_complete,
    }


def _mint(user, *, method: str) -> RefreshToken:
    refresh = RefreshToken.for_user(user)
    refresh["amr"] = [method]
    for claim, value in _org_claims(user).items():
        refresh[claim] = value
    return refresh


class TokenService:
    @staticmethod
    def issue_session(
        user: User,
        *,
        method: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict:
        """Gate-check the user, record the attempt, and mint a token pair.

        Raises ``ValueError`` with the same messages AuthService always used,
        so the exception-handler behavior (generic 400) is unchanged.
        """
        if not user.is_email_verified:
            LoginAttempt.objects.create(
                email=user.email,
                ip_address=ip_address or None,
                user_agent=user_agent,
                success=False,
                user=user,
            )
            raise ValueError("Please verify your email before logging in.")

        if not user.is_active:
            LoginAttempt.objects.create(
                email=user.email,
                ip_address=ip_address or None,
                user_agent=user_agent,
                success=False,
                user=user,
            )
            security_logger.warning(
                "Login attempt on deactivated account",
                extra={"user_id": str(user.id), "ip": ip_address},
            )
            raise ValueError("This account has been deactivated.")

        LoginAttempt.objects.create(
            email=user.email,
            ip_address=ip_address or None,
            user_agent=user_agent,
            success=True,
            user=user,
        )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = _mint(user, method=method)
        audit_log(
            "user.login",
            user=user,
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            metadata={"ip": ip_address, "method": method},
        )

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": _user_payload(user),
        }

    @staticmethod
    def rotate_session(*, refresh_token: str) -> dict:
        """Validate, blacklist, and replace a refresh token.

        This is real rotation: the presented token is blacklisted and a
        fresh one minted with org claims re-derived from the DB. The
        previous implementation returned the SAME refresh string —
        ROTATE_REFRESH_TOKENS only applies to SimpleJWT's own (unrouted)
        serializer, so nothing ever rotated or blacklisted on this path.
        """
        try:
            old = RefreshToken(refresh_token)  # verifies signature/expiry/blacklist
            user = User.objects.get(id=old["user_id"], is_active=True)
        except (TokenError, User.DoesNotExist, KeyError):
            raise ValueError("Refresh token is invalid or expired.") from None

        # Preserve how the session originally authenticated across rotations.
        amr = old.get("amr") or ["pwd"]
        method = amr[0] if isinstance(amr, list) and amr else "pwd"

        try:
            old.blacklist()
        except Exception:
            # Blacklist table hiccups must not lock every user out of refresh.
            security_logger.warning("Refresh-token blacklist write failed on rotation")

        refresh = _mint(user, method=method)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def revoke_all_for_users(user_ids, *, exclude_jti: str | None = None) -> int:
        """Blacklist every outstanding refresh token for ``user_ids``.

        Used when a member is removed from an org and when SSO enforcement
        flips on. ``exclude_jti`` keeps the acting session alive so an admin
        doesn't log themselves out mid-settings. Returns how many tokens
        were newly blacklisted.
        """
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        outstanding = OutstandingToken.objects.filter(user_id__in=list(user_ids))
        if exclude_jti:
            outstanding = outstanding.exclude(jti=exclude_jti)

        revoked = 0
        for token in outstanding.iterator():
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            revoked += int(created)
        return revoked
