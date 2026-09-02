"""SAML sign-in through a pluggable bridge (SSOReady by default, WorkOS
as a drop-in alternative via SSO_BRIDGE_PROVIDER).

Both providers do the same job: they terminate the customer IdP's SAML
(the CVE-prone XML handling lives with them, never here) and hand this
service a verified profile over HTTPS. The flow is the classic hosted
triangle, driven with plain ``requests``:

1. The SPA posts the user's work email to /auth/saml/start/;
   ``authorize_redirect`` resolves the domain to an org with a bridge
   connection id and answers the provider's redirect URL.
2. The IdP round-trip lands the browser on /auth/saml/callback/ (a GET,
   not an XHR); ``complete`` redeems the callback code for a profile and
   resolves the user.
3. Because the callback is a top-level browser navigation, tokens never
   ride the redirect URL — the callback view mints a one-time exchange
   code (``mint_exchange_code``) and the SPA immediately trades it for
   the session at /auth/token-exchange/.

Identity and trust rules (both providers):

- The profile's organization id MUST equal the org the flow started for
  (bound by our signed ``state``) — without this, a code minted by any
  other connection on our bridge account could mint a session in the
  wrong tenant.
- The asserted email is org-authoritative: a bridge connection belongs
  to exactly one customer org and only relays that org's IdP, so
  email-match linking and JIT provisioning are safe within that org.
- JIT grants the org's ``default_role`` inside a transaction so the seat
  gate can roll the new account back cleanly.
"""
import logging
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import Organization, OrgDomain, SocialIdentity, User
from core.exceptions import CanseeException, PermissionDenied, ResourceNotFound
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

SSOREADY_REDIRECT_URL = "https://api.ssoready.com/v1/saml/redirect"
SSOREADY_REDEEM_URL = "https://api.ssoready.com/v1/saml/redeem"
WORKOS_AUTHORIZE_URL = "https://api.workos.com/sso/authorize"
WORKOS_TOKEN_URL = "https://api.workos.com/sso/token"

# How long the signed state (start -> callback round-trip) stays valid.
_STATE_MAX_AGE_SECONDS = 600
# How long the one-time browser-handoff code stays redeemable.
_EXCHANGE_TTL_SECONDS = 60
_EXCHANGE_CACHE_PREFIX = "sso_xc:"


def _provider() -> str:
    return (settings.SSO_BRIDGE_PROVIDER or "ssoready").strip().lower()


def _bridge_configured() -> bool:
    if _provider() == "workos":
        return bool(settings.WORKOS_API_KEY and settings.WORKOS_CLIENT_ID)
    return bool(settings.SSOREADY_API_KEY)


def _callback_url() -> str:
    return settings.BACKEND_PUBLIC_URL.rstrip("/") + "/api/v1/auth/saml/callback/"


def _org_for_email(email: str) -> Organization:
    """Resolve a work email's DOMAIN to a SAML-connected org, or 404/503."""
    record = (
        OrgDomain.objects.select_related("organization")
        .filter(domain=email.rsplit("@", 1)[-1], verified_at__isnull=False)
        .first()
    )
    org = record.organization if record else None
    if org is None or not org.sso_connection_id:
        raise ResourceNotFound(
            "Single sign-on isn't set up for this email domain."
        )
    # Checked AFTER the org lookup: sso_methods_for offers the button on
    # sso_connection_id alone, so missing keys must surface as a visible
    # 503 (an ops misconfig), never masquerade as "not set up".
    if not _bridge_configured():
        raise CanseeException(
            "Company SSO is temporarily unavailable.",
            code="sso_unavailable",
            status_code=503,
        )
    return org


def authorize_redirect(*, email: str) -> str:
    """Resolve a work email to the bridge's hosted authorize URL."""
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValueError("Enter your work email address.")
    org = _org_for_email(email)
    state = signing.dumps({"org": str(org.id), "hint": email})

    if _provider() == "workos":
        query = urlencode(
            {
                "client_id": settings.WORKOS_CLIENT_ID,
                "redirect_uri": _callback_url(),
                "response_type": "code",
                "organization": org.sso_connection_id,
                "state": state,
            }
        )
        return f"{WORKOS_AUTHORIZE_URL}?{query}"

    # SSOReady: the redirect URL is minted by their API; our signed state
    # rides along and comes back in the redeem response.
    response = requests.post(
        SSOREADY_REDIRECT_URL,
        json={
            "organizationExternalId": org.sso_connection_id,
            "state": state,
        },
        headers={"Authorization": f"Bearer {settings.SSOREADY_API_KEY}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["redirectUrl"]


def _redeem_profile(*, code: str, state: str) -> tuple[dict, str]:
    """Redeem the callback code at the bridge.

    Returns (normalized profile, state) where the profile is
    {subject, email, full_name, org_connection_id} regardless of provider.
    """
    if _provider() == "workos":
        token_response = requests.post(
            WORKOS_TOKEN_URL,
            data={
                "client_id": settings.WORKOS_CLIENT_ID,
                "client_secret": settings.WORKOS_API_KEY,
                "grant_type": "authorization_code",
                "code": code,
            },
            timeout=10,
        )
        token_response.raise_for_status()
        profile = token_response.json()["profile"]
        full_name = " ".join(
            p.strip()
            for p in (profile.get("first_name"), profile.get("last_name"))
            if p and p.strip()
        )
        return (
            {
                "subject": profile["id"],
                "email": (profile.get("email") or "").strip().lower(),
                "full_name": full_name,
                "org_connection_id": profile.get("organization_id"),
            },
            state,
        )

    redeem_response = requests.post(
        SSOREADY_REDEEM_URL,
        json={"samlAccessCode": code},
        headers={"Authorization": f"Bearer {settings.SSOREADY_API_KEY}"},
        timeout=10,
    )
    redeem_response.raise_for_status()
    data = redeem_response.json()
    email = (data.get("email") or "").strip().lower()
    attributes = data.get("attributes") or {}
    full_name = (
        attributes.get("displayName")
        or attributes.get("name")
        or " ".join(
            p.strip()
            for p in (attributes.get("firstName"), attributes.get("lastName"))
            if p and p.strip()
        )
    )
    return (
        {
            # SSOReady's redeem has no separate durable subject; the
            # asserted email under the org's own connection is the stable
            # key, namespaced by tenant in SocialIdentity's uniqueness.
            "subject": email,
            "email": email,
            "full_name": full_name or "",
            "org_connection_id": data.get("organizationExternalId"),
        },
        # Our signed state rode through SSOReady and returns here; the
        # callback query param (if any) is the fallback.
        data.get("state") or state,
    )


def complete(*, code: str, state: str) -> dict:
    """Redeem the callback code and resolve the user.

    Returns {user, org, joined_org, is_new_user} — the same shape as the
    Google and Entra lanes.
    """
    profile, state = _redeem_profile(code=code, state=state)

    try:
        payload = signing.loads(state or "", max_age=_STATE_MAX_AGE_SECONDS)
    except signing.BadSignature:
        # SignatureExpired subclasses BadSignature — both mean the same
        # thing to the person staring at the browser.
        raise ValueError("This sign-in link expired. Start again.") from None

    try:
        org = Organization.objects.get(id=payload["org"])
    except (Organization.DoesNotExist, KeyError, ValueError):
        raise ValueError("This sign-in link expired. Start again.") from None

    # The profile MUST belong to the organization this flow started for.
    if profile["org_connection_id"] != org.sso_connection_id:
        raise PermissionDenied("SSO profile did not match the organization.")

    email = profile["email"]
    if not email:
        raise ValueError("The identity provider did not assert an email.")
    subject = profile["subject"]
    full_name = profile["full_name"] or email.split("@", 1)[0]

    # 1. Stable-key lookup.
    identity = (
        SocialIdentity.objects.select_related("user")
        .filter(provider="saml", subject=subject, tenant=org.sso_connection_id)
        .first()
    )
    user = identity.user if identity else None

    joined_org = False
    is_new_user = False

    # 2. One-time link to an existing account by email (org-authoritative
    #    under the bridge connection — see the module docstring).
    if user is None:
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            identity = SocialIdentity.objects.create(
                user=user,
                provider="saml",
                subject=subject,
                tenant=org.sso_connection_id,
                email_at_link=email,
            )

    # 3. JIT provisioning against the flow's org.
    if user is None:
        from django.db import transaction

        from apps.accounts.services.org_service import OrgService

        # Atomic: a seat-cap rejection inside add_member must roll the
        # just-created user back, or it strands a passwordless orphan
        # account (see the Google/Entra lanes).
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=None,
                full_name=full_name,
                company_name=org.name,
                is_email_verified=True,
            )
            is_new_user = True
            identity = SocialIdentity.objects.create(
                user=user,
                provider="saml",
                subject=subject,
                tenant=org.sso_connection_id,
                email_at_link=email,
            )
            OrgService.add_member(
                organization=org,
                user=user,
                role=org.default_role,
                joined_via="sso_jit",
            )
        joined_org = True
        audit_log(
            "org.member_jit_joined",
            user=user,
            action="create",
            resource_type="organization",
            resource_id=str(org.id),
            metadata={"sso_connection_id": org.sso_connection_id},
        )

    if identity is not None:
        identity.last_login_at = timezone.now()
        identity.save(update_fields=["last_login_at"])

    audit_log(
        "user.login",
        user=user,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"method": "saml", "bridge": _provider()},
    )

    return {
        "user": user,
        "org": org,
        "joined_org": joined_org,
        "is_new_user": is_new_user,
    }


def mint_exchange_code(session_payload: dict) -> str:
    """Stash a session payload behind a one-time browser-handoff code."""
    code = secrets.token_urlsafe(32)
    cache.set(f"{_EXCHANGE_CACHE_PREFIX}{code}", session_payload, _EXCHANGE_TTL_SECONDS)
    return code


def redeem_exchange_code(code: str) -> dict | None:
    """Redeem (and burn) a one-time exchange code. None when invalid."""
    key = f"{_EXCHANGE_CACHE_PREFIX}{code}"
    payload = cache.get(key)
    # get-then-delete is not atomic, so two exactly-simultaneous redeems
    # could both win. Acceptable for a 60-second, single-use, 256-bit
    # random code that only ever travels one browser's URL bar.
    cache.delete(key)
    return payload
