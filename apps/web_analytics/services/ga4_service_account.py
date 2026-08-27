"""
Service-account auth for the FetchBot-owned GA4 pool property.

The hosted Google-tag source (see ga4_hosted.py) provisions data
streams in a property we control and reads them back — both with a
service account that the operator has granted Editor on that property.

Google's SDKs are deliberately avoided (requests is the house HTTP
library): the JWT-bearer grant is ~30 lines with the cryptography
package that field encryption already requires. The minted access
token is cached in Redis; the key JSON itself is never cached.
"""

from __future__ import annotations

import base64
import json
import logging
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps")

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# analytics.edit covers Admin API stream management AND Data API reads.
SCOPE = "https://www.googleapis.com/auth/analytics.edit"

_TOKEN_CACHE_KEY = "wa:ga4:sa_token"
# Google issues 3600s tokens; cache slightly under that.
_TOKEN_CACHE_SECONDS = 3000


def is_configured() -> bool:
    return bool(
        getattr(settings, "GA4_SA_CREDENTIALS_JSON", "")
        and getattr(settings, "GA4_HOSTED_PROPERTY_ID", "")
    )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _signed_assertion(creds: dict) -> str:
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = _b64url(
        json.dumps(
            {
                "iss": creds["client_email"],
                "scope": SCOPE,
                "aud": TOKEN_ENDPOINT,
                "iat": now,
                "exp": now + 3600,
            }
        ).encode()
    )
    signing_input = f"{header}.{claims}".encode("ascii")
    private_key = serialization.load_pem_private_key(
        creds["private_key"].encode(), password=None
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header}.{claims}.{_b64url(signature)}"


def get_access_token() -> str | None:
    """Mint (or reuse) a service-account access token. None on any
    failure — misconfiguration, bad key, Google error — all logged."""
    if not is_configured():
        return None

    try:
        cached = cache.get(_TOKEN_CACHE_KEY)
    except Exception:
        cached = None
    if cached:
        return cached

    try:
        creds = json.loads(settings.GA4_SA_CREDENTIALS_JSON)
        assertion = _signed_assertion(creds)
    except (ValueError, KeyError, TypeError) as exc:
        logger.error("GA4 service-account credentials are unusable: %s", exc)
        return None

    try:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token", "")
    except (requests.RequestException, ValueError) as exc:
        logger.warning("GA4 service-account token exchange failed: %s", exc)
        return None

    if not token:
        logger.warning("GA4 service-account token exchange returned no access_token")
        return None
    try:
        cache.set(_TOKEN_CACHE_KEY, token, _TOKEN_CACHE_SECONDS)
    except Exception:
        pass
    return token
