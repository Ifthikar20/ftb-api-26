"""
Google Search Console OAuth flow (offline access, webmasters.readonly).

Separate from apps.accounts.services.oauth_service, which is an
identity-only login flow that discards Google tokens. This flow
requests offline access, persists tokens on the per-website
Integration(type="gsc") row, and keeps them fresh via the registered
refresh_token_fn (see apps/search_console/apps.py).

The OAuth state parameter is a signed payload (django.core.signing)
carrying the website and user ids: the callback arrives from Google
without a JWT, so the signature is what proves the flow was initiated
by an authenticated owner of the website.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.search_console.services import gsc_client
from core.integrations import get_registry

logger = logging.getLogger("apps")

STATE_SALT = "gsc-oauth"
STATE_MAX_AGE_SECONDS = 600
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"


def _config():
    cfg = get_registry().get("gsc")
    if cfg is None:
        raise RuntimeError("gsc integration is not registered")
    return cfg


def is_configured() -> bool:
    return gsc_client.is_configured()


# -- Authorize / state ------------------------------------------------------

def build_authorize_url(*, website, user) -> str:
    """Build the Google consent URL for connecting GSC to a website."""
    creds = _config().get_credentials()
    state = signing.dumps(
        {"website_id": str(website.id), "user_id": str(user.id)},
        salt=STATE_SALT,
    )
    params = {
        "client_id": creds["client_id"],
        "redirect_uri": settings.GSC_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(creds["scopes"]),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
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

    Returns Google's token payload: {"access_token", "refresh_token",
    "expires_in", ...}. Raises requests.RequestException on failure.
    """
    creds = _config().get_credentials()
    resp = requests.post(
        creds["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "redirect_uri": settings.GSC_OAUTH_REDIRECT_URI,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def complete_connection(*, website, tokens: dict):
    """Create or update the gsc Integration row with fresh tokens.

    Google only returns refresh_token on the first consent; on a
    re-connect without one we keep the previously stored value.
    """
    from apps.websites.models import Integration

    expires_in = int(tokens.get("expires_in") or 3600)
    integration, _created = Integration.objects.get_or_create(
        website=website, type="gsc"
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


# -- Property matching -------------------------------------------------------

def _website_host(website) -> str:
    host = urlparse(website.url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def auto_match_property(integration) -> str | None:
    """Match the website's domain against the account's GSC properties.

    Preference order: sc-domain property (covers every protocol and
    subdomain), then https/http URL-prefix variants. Unverified
    properties are skipped. Stores the outcome in integration.metadata:
    either site_url, or pending_property_selection plus the available
    list for the UI picker.
    """
    sites = gsc_client.list_sites(integration.access_token)
    usable = [s for s in sites if s.get("permission_level") != "siteUnverifiedUser"]

    host = _website_host(integration.website)
    candidates = [
        f"sc-domain:{host}",
        f"https://{host}/",
        f"https://www.{host}/",
        f"http://{host}/",
        f"http://www.{host}/",
    ]
    by_url = {s["site_url"]: s for s in usable}
    match = next((c for c in candidates if c in by_url), None)

    metadata = dict(integration.metadata or {})
    metadata["available_sites"] = usable
    if match:
        metadata["site_url"] = match
        metadata.pop("pending_property_selection", None)
    else:
        metadata.pop("site_url", None)
        metadata["pending_property_selection"] = True
    integration.metadata = metadata
    integration.save(update_fields=["metadata", "updated_at"])
    return match


# -- Disconnect / refresh -----------------------------------------------------

def disconnect(integration) -> None:
    """Revoke the Google grant (best effort) and deactivate the row.

    Stored metrics are intentionally retained so history survives a
    reconnect.
    """
    token = integration.refresh_token or integration.access_token
    if token:
        try:
            requests.post(REVOKE_ENDPOINT, data={"token": token}, timeout=10)
        except requests.RequestException as exc:
            logger.warning("GSC token revoke failed (ignored): %s", exc)

    integration.access_token = ""
    integration.refresh_token = ""
    integration.token_expires_at = None
    integration.is_active = False
    metadata = dict(integration.metadata or {})
    metadata.pop("site_url", None)
    metadata.pop("pending_property_selection", None)
    integration.metadata = metadata
    integration.save()


def refresh_access_token(integration) -> None:
    """Refresh the stored access token in place.

    Registered as the gsc refresh_token_fn — called by
    apps.websites.tasks.refresh_expiring_tokens (every 15 minutes) and
    inline before a sync when the token is near expiry.

    A Google invalid_grant response means the user revoked access (or
    the refresh token aged out): the integration is deactivated so the
    UI can prompt a reconnect. Any other failure raises so the beat
    task counts it and retries next cycle.
    """
    if not integration.refresh_token:
        logger.warning(
            "GSC integration %s has no refresh token; deactivating", integration.pk
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
            "GSC refresh got invalid_grant for integration %s; deactivating",
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
