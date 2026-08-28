"""
Google Analytics 4 OAuth flow (offline access, analytics.readonly).

Mirrors apps/search_console/services/oauth_service.py: offline access,
tokens persisted on the per-website Integration(type="ga") row, kept
fresh via the refresh_token_fn registered in apps/web_analytics/apps.py.

The OAuth state parameter is a signed payload (django.core.signing)
carrying the website and user ids: the callback arrives from Google
without a JWT, so the signature is what proves the flow was initiated
by an authenticated owner of the website.

Deliberate deviations from the GSC flow:
  - include_granted_scopes is omitted, so this consent stays scoped to
    analytics.readonly instead of aggregating prior grants.
  - disconnect() only revokes the Google grant when the website has no
    other active Google integration: Google keeps ONE grant per
    user+client, so revoking the GA4 token would also kill GSC.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.web_analytics.services import ga4_client
from core.integrations import get_registry

logger = logging.getLogger("apps")

STATE_SALT = "ga4-oauth"
STATE_MAX_AGE_SECONDS = 600
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

# Google integration types that share the single per-user grant.
GOOGLE_GRANT_TYPES = ("gsc",)


def _config():
    cfg = get_registry().get("ga")
    if cfg is None:
        raise RuntimeError("ga integration is not registered")
    return cfg


def is_configured() -> bool:
    return ga4_client.is_configured()


# -- Authorize / state ------------------------------------------------------

def build_authorize_url(*, website, user) -> str:
    """Build the Google consent URL for connecting GA4 to a website."""
    creds = _config().get_credentials()
    state = signing.dumps(
        {"website_id": str(website.id), "user_id": str(user.id)},
        salt=STATE_SALT,
    )
    params = {
        "client_id": creds["client_id"],
        "redirect_uri": settings.GA4_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(creds["scopes"]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{creds['authorize_url']}?{urlencode(params)}"


def parse_state(state: str) -> dict:
    """Verify and decode the signed state. Raises signing.BadSignature
    (or SignatureExpired) on tampering or expiry."""
    return signing.loads(state, salt=STATE_SALT, max_age=STATE_MAX_AGE_SECONDS)


# -- Token exchange / storage -----------------------------------------------

def exchange_code(code: str) -> dict:
    """Exchange an authorization code for tokens.

    Returns Google's token payload. Raises requests.RequestException on
    failure.
    """
    creds = _config().get_credentials()
    resp = requests.post(
        creds["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "redirect_uri": settings.GA4_OAUTH_REDIRECT_URI,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def complete_connection(*, website, tokens: dict):
    """Create or update the ga Integration row with fresh tokens.

    Google only returns refresh_token on the first consent; on a
    re-connect without one we keep the previously stored value.
    """
    from apps.websites.models import Integration

    expires_in = int(tokens.get("expires_in") or 3600)
    integration, _created = Integration.objects.get_or_create(
        website=website, type="ga"
    )
    integration.access_token = tokens.get("access_token", "")
    new_refresh = tokens.get("refresh_token", "")
    if new_refresh:
        integration.refresh_token = new_refresh
    integration.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
    integration.is_active = True
    integration.metadata = dict(integration.metadata or {})
    integration.metadata.pop("revoked_at", None)
    integration.save()
    return integration


# -- Property selection -------------------------------------------------------

def auto_select_property(integration) -> str | None:
    """List the account's GA4 properties and auto-select when unambiguous.

    GA4 property summaries carry no site URL, so unlike GSC there is no
    domain matching: exactly one property auto-selects, anything else
    stores the list and flags pending_property_selection for the picker.
    """
    properties = ga4_client.list_account_summaries(
        integration.access_token, website_id=str(integration.website_id)
    )

    metadata = dict(integration.metadata or {})
    metadata["available_properties"] = properties
    if len(properties) == 1:
        metadata["property_id"] = properties[0]["property_id"]
        metadata["property_display_name"] = properties[0]["display_name"]
        metadata.pop("pending_property_selection", None)
        selected = properties[0]["property_id"]
    else:
        metadata.pop("property_id", None)
        metadata.pop("property_display_name", None)
        metadata["pending_property_selection"] = True
        selected = None
    integration.metadata = metadata
    integration.save(update_fields=["metadata", "updated_at"])
    return selected


def select_property(integration, property_id: str) -> bool:
    """Pin one of the account's properties. Returns False when the id is
    not in the accessible list (refetched when the cache is empty)."""
    available = {
        p["property_id"]: p
        for p in (integration.metadata or {}).get("available_properties", [])
    }
    if not available:
        available = {
            p["property_id"]: p
            for p in ga4_client.list_account_summaries(
                integration.access_token, website_id=str(integration.website_id)
            )
        }
    chosen = available.get(str(property_id))
    if chosen is None:
        return False

    metadata = dict(integration.metadata or {})
    metadata["property_id"] = chosen["property_id"]
    metadata["property_display_name"] = chosen["display_name"]
    metadata["available_properties"] = list(available.values())
    metadata.pop("pending_property_selection", None)
    integration.metadata = metadata
    integration.save(update_fields=["metadata", "updated_at"])
    return True


# -- Disconnect / refresh -----------------------------------------------------

def _has_other_google_grant(integration) -> bool:
    from apps.websites.models import Integration

    return Integration.objects.filter(
        website=integration.website,
        type__in=GOOGLE_GRANT_TYPES,
        is_active=True,
    ).exists()


def disconnect(integration) -> None:
    """Deactivate the row; revoke the Google grant only when it is not
    shared with another active Google integration on this website."""
    token = integration.refresh_token or integration.access_token
    if token and not _has_other_google_grant(integration):
        try:
            requests.post(REVOKE_ENDPOINT, data={"token": token}, timeout=10)
        except requests.RequestException as exc:
            logger.warning("GA4 token revoke failed (ignored): %s", exc)

    integration.access_token = ""
    integration.refresh_token = ""
    integration.token_expires_at = None
    integration.is_active = False
    metadata = dict(integration.metadata or {})
    metadata.pop("property_id", None)
    metadata.pop("property_display_name", None)
    metadata.pop("pending_property_selection", None)
    integration.metadata = metadata
    integration.save()


def refresh_access_token(integration) -> None:
    """Refresh the stored access token in place.

    Registered as the ga refresh_token_fn — called by
    apps.websites.tasks.refresh_expiring_tokens (every 15 minutes) and
    inline before a snapshot fetch when the token is near expiry.

    A Google invalid_grant response means the user revoked access (or
    the refresh token aged out): the integration is deactivated so the
    UI can prompt a reconnect. Any other failure raises so the beat
    task counts it and retries next cycle.
    """
    if not integration.refresh_token:
        logger.warning(
            "GA4 integration %s has no refresh token; deactivating", integration.pk
        )
        integration.is_active = False
        integration.save(update_fields=["is_active", "updated_at"])
        return

    creds = _config().get_credentials()
    resp = requests.post(
        creds["token_url"],
        data={
            "grant_type": "refresh_token",
            "refresh_token": integration.refresh_token,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        },
        timeout=10,
    )
    if resp.status_code == 400 and "invalid_grant" in resp.text:
        logger.warning(
            "GA4 refresh got invalid_grant for integration %s; deactivating",
            integration.pk,
        )
        integration.is_active = False
        metadata = dict(integration.metadata or {})
        metadata["revoked_at"] = timezone.now().isoformat()
        integration.metadata = metadata
        integration.save(update_fields=["is_active", "metadata", "updated_at"])
        return
    resp.raise_for_status()
    tokens = resp.json()

    integration.access_token = tokens.get("access_token", "")
    integration.token_expires_at = timezone.now() + timedelta(
        seconds=int(tokens.get("expires_in") or 3600)
    )
    integration.save(update_fields=["access_token", "token_expires_at", "updated_at"])
