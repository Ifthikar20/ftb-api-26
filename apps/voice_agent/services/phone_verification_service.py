"""Phone-number ownership verification (MFA) service.

When a user tries to add a phone number to their voice agent we must prove
they actually own that number — otherwise an attacker could attach someone
else's DID and intercept calls. Flow:

  1. ``start()`` generates a 6-digit code, stores its HMAC in a
     ``PhoneVerification`` row, and asks the telephony vendor to deliver it
     either as an SMS or as an automated voice call that reads it aloud.
  2. The user posts the code back to ``confirm()``. On success the row is
     marked verified and a short-lived token (the row id) is returned.
  3. The PhoneNumber create endpoint requires that token plus matching
     number, and only then persists the row with ``is_verified=True``.

The vendor side is intentionally pluggable. Today we wire Telnyx via the
existing :mod:`telnyx_service` module; Twilio can be added later behind the
same interface. In DEBUG mode with no API key configured we log the OTP so
local development still works without burning real SMS credits.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.utils import timezone

from apps.voice_agent.models import PhoneVerification

logger = logging.getLogger("apps")

CODE_TTL = timedelta(minutes=10)
CODE_LENGTH = 6


class PhoneVerificationError(RuntimeError):
    """Raised for any user-visible verification failure."""


def _hash_code(code: str) -> str:
    secret = getattr(settings, "SECRET_KEY", "").encode()
    return hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def _send_via_vendor(number: str, code: str, channel: str) -> str:
    """Hand off the OTP to the configured telephony vendor.

    Returns the vendor's request id (message SID, call SID, etc.) for tracing.
    Raises :class:`PhoneVerificationError` if the vendor rejects the request.
    """
    api_key = getattr(settings, "TELNYX_API_KEY", "")
    if not api_key:
        # Dev fallback: surface the code in logs so engineers can complete
        # the flow without provisioning a real SMS sender.
        if getattr(settings, "DEBUG", False):
            logger.warning(
                "phone_verification_dev_code",
                extra={"number": number, "code": code, "channel": channel},
            )
            return "dev-no-vendor"
        raise PhoneVerificationError(
            "Telephony vendor is not configured; cannot send verification code."
        )

    try:
        if channel == PhoneVerification.CHANNEL_SMS:
            from apps.voice_agent.services.telnyx_service import TelnyxService

            resp = TelnyxService.send_sms(
                to=number,
                text=(
                    f"Your verification code is {code}. "
                    "It expires in 10 minutes."
                ),
            )
            return str(resp.get("data", {}).get("id", ""))

        # CHANNEL_CALL — place an automated voice call that reads the code.
        from apps.voice_agent.services.telnyx_service import TelnyxService

        resp = TelnyxService.place_verification_call(to=number, code=code)
        return str(resp.get("data", {}).get("call_control_id", ""))
    except Exception as e:  # noqa: BLE001 — vendor errors are user-visible
        logger.warning(
            "phone_verification_vendor_failed",
            extra={"number": number, "channel": channel, "error": str(e)},
        )
        raise PhoneVerificationError(
            "Could not deliver verification code. Please try again."
        ) from e


def start(
    *,
    website,
    number: str,
    channel: str,
    requested_by=None,
) -> PhoneVerification:
    """Issue a fresh OTP for ``number`` and return the persisted challenge."""
    if channel not in {PhoneVerification.CHANNEL_SMS, PhoneVerification.CHANNEL_CALL}:
        raise PhoneVerificationError("channel must be 'sms' or 'call'.")
    if not number or not number.startswith("+"):
        raise PhoneVerificationError("Number must be in E.164 format (e.g. +12025551234).")

    # Invalidate any prior pending challenges for the same (website, number)
    # so the latest code is the only one that can succeed.
    PhoneVerification.objects.filter(
        website=website,
        number=number,
        status=PhoneVerification.STATUS_PENDING,
    ).update(status=PhoneVerification.STATUS_EXPIRED)

    code = _generate_code()
    verification = PhoneVerification.objects.create(
        website=website,
        requested_by=requested_by,
        number=number,
        channel=channel,
        code_hash=_hash_code(code),
        expires_at=timezone.now() + CODE_TTL,
    )
    try:
        verification.vendor_request_id = _send_via_vendor(number, code, channel)
        verification.save(update_fields=["vendor_request_id", "updated_at"])
    except PhoneVerificationError:
        verification.status = PhoneVerification.STATUS_FAILED
        verification.save(update_fields=["status", "updated_at"])
        raise
    return verification


def confirm(*, website, verification_id: str, code: str) -> PhoneVerification:
    """Validate ``code`` against the stored challenge.

    On success the row is flipped to ``verified`` and returned. The caller
    can then pass ``verification_id`` to the PhoneNumber create endpoint
    to persist the actual number.
    """
    try:
        verification = PhoneVerification.objects.get(id=verification_id, website=website)
    except PhoneVerification.DoesNotExist as e:
        raise PhoneVerificationError("Verification challenge not found.") from e

    if verification.status != PhoneVerification.STATUS_PENDING:
        raise PhoneVerificationError("This verification is no longer pending.")
    if verification.expires_at < timezone.now():
        verification.status = PhoneVerification.STATUS_EXPIRED
        verification.save(update_fields=["status", "updated_at"])
        raise PhoneVerificationError("Verification code has expired. Please request a new one.")
    if verification.attempts >= verification.max_attempts:
        verification.status = PhoneVerification.STATUS_FAILED
        verification.save(update_fields=["status", "updated_at"])
        raise PhoneVerificationError("Too many failed attempts. Please request a new code.")

    verification.attempts += 1
    if not hmac.compare_digest(verification.code_hash, _hash_code(code or "")):
        verification.save(update_fields=["attempts", "updated_at"])
        raise PhoneVerificationError("Incorrect verification code.")

    verification.status = PhoneVerification.STATUS_VERIFIED
    verification.save(update_fields=["status", "attempts", "updated_at"])
    return verification


def consume(*, website, verification_id: str, number: str) -> Optional[PhoneVerification]:
    """Look up a verified challenge for ``number`` so the create endpoint
    can confirm the user just proved ownership. Returns the row or ``None``.
    """
    if not verification_id:
        return None
    try:
        verification = PhoneVerification.objects.get(
            id=verification_id,
            website=website,
            number=number,
            status=PhoneVerification.STATUS_VERIFIED,
        )
    except PhoneVerification.DoesNotExist:
        return None
    return verification
