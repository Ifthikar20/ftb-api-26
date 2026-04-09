"""Thin Telnyx REST wrapper for outbound calling.

For the LiveKit + Telnyx outbound flow we don't actually call Telnyx at dial time
(LiveKit places the SIP INVITE via the cached SIP credentials). This module exists
for the one-time bootstrap step: confirming a SIP connection (a.k.a. trunk) exists
and listing/purchasing DIDs that are then attached to it. Webhook handling for
outbound MVP is intentionally omitted — call state comes from LiveKit room events.
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger("apps")

TELNYX_API_BASE = "https://api.telnyx.com/v2"


class TelnyxConfigError(RuntimeError):
    """Raised when Telnyx credentials/connection are missing or invalid."""


class TelnyxService:
    """Minimal Telnyx REST client used by the outbound dialer bootstrap."""

    @staticmethod
    def _api_key() -> str:
        key = getattr(settings, "TELNYX_API_KEY", "")
        if not key:
            raise TelnyxConfigError("TELNYX_API_KEY is not set")
        return key

    @classmethod
    def _headers(cls) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {cls._api_key()}",
            "Content-Type": "application/json",
        }

    @classmethod
    def get_sip_connection(cls, connection_id: str | None = None) -> dict[str, Any]:
        """Return the configured SIP connection (a.k.a. trunk).

        Confirms the credentials in settings can authenticate against Telnyx and
        the SIP connection that LiveKit will dial through actually exists.
        """
        cid = connection_id or getattr(settings, "TELNYX_OUTBOUND_CONNECTION_ID", "")
        if not cid:
            raise TelnyxConfigError("TELNYX_OUTBOUND_CONNECTION_ID is not set")

        resp = requests.get(
            f"{TELNYX_API_BASE}/credential_connections/{cid}",
            headers=cls._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    @classmethod
    def list_phone_numbers(cls) -> list[dict[str, Any]]:
        """Return all phone numbers on the account."""
        resp = requests.get(
            f"{TELNYX_API_BASE}/phone_numbers",
            headers=cls._headers(),
            params={"page[size]": 250},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    @classmethod
    def attach_number_to_connection(
        cls, *, phone_number_id: str, connection_id: str
    ) -> dict[str, Any]:
        """Bind a Telnyx-owned DID to a SIP connection so it can be used as caller ID."""
        resp = requests.patch(
            f"{TELNYX_API_BASE}/phone_numbers/{phone_number_id}",
            headers=cls._headers(),
            json={"connection_id": connection_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    @classmethod
    def sip_address(cls) -> str:
        """SIP URI LiveKit dials when placing an outbound call via Telnyx."""
        return getattr(settings, "TELNYX_SIP_ADDRESS", "sip.telnyx.com")
