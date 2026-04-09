"""Tests for phone-number ownership MFA.

The vendor side (Telnyx SMS / call) is patched out — we only verify the
state-machine: code generation/hashing, expiry, attempt limit, replay
prevention, and the ``consume`` gate that the PhoneNumber create endpoint
relies on. The vendor integration itself is exercised by Telnyx mocks in
``test_outbound_dialer``.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.voice_agent.models import PhoneVerification
from apps.voice_agent.services import phone_verification_service as pvs
from apps.websites.models import Website


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="owner@acme.test", password="x", full_name="Owner"
    )


@pytest.fixture
def website(db, user):
    return Website.objects.create(name="Acme", url="https://acme.test", user=user)


@pytest.fixture
def stub_vendor():
    """Patch out the real Telnyx call so tests don't need API keys."""
    with patch.object(pvs, "_send_via_vendor", return_value="stub-msg-id"):
        yield


# ── start() ────────────────────────────────────────────────────────────────────


def test_start_creates_pending_row(db, website, user, stub_vendor):
    v = pvs.start(website=website, number="+12025551234", channel="sms", requested_by=user)
    assert v.status == PhoneVerification.STATUS_PENDING
    assert v.channel == "sms"
    assert v.code_hash  # was hashed and stored
    assert v.expires_at > timezone.now()
    assert v.vendor_request_id == "stub-msg-id"


def test_start_rejects_invalid_channel(db, website, stub_vendor):
    with pytest.raises(pvs.PhoneVerificationError, match="channel"):
        pvs.start(website=website, number="+12025551234", channel="email")


def test_start_rejects_non_e164(db, website, stub_vendor):
    with pytest.raises(pvs.PhoneVerificationError, match="E.164"):
        pvs.start(website=website, number="2025551234", channel="sms")


def test_start_invalidates_prior_pending_challenges(db, website, stub_vendor):
    """Latest code wins — a stale challenge can never be confirmed."""
    first = pvs.start(website=website, number="+12025551234", channel="sms")
    second = pvs.start(website=website, number="+12025551234", channel="sms")
    first.refresh_from_db()
    assert first.status == PhoneVerification.STATUS_EXPIRED
    assert second.status == PhoneVerification.STATUS_PENDING


def test_start_marks_failed_when_vendor_raises(db, website):
    with patch.object(
        pvs, "_send_via_vendor", side_effect=pvs.PhoneVerificationError("nope")
    ):
        with pytest.raises(pvs.PhoneVerificationError):
            pvs.start(website=website, number="+12025551234", channel="sms")
    v = PhoneVerification.objects.get(number="+12025551234")
    assert v.status == PhoneVerification.STATUS_FAILED


# ── confirm() ──────────────────────────────────────────────────────────────────


def _start_with_known_code(website):
    """Bypass the random code so we can confirm() in tests."""
    code = "654321"
    with patch.object(pvs, "_generate_code", return_value=code), patch.object(
        pvs, "_send_via_vendor", return_value="stub"
    ):
        v = pvs.start(website=website, number="+12025557777", channel="sms")
    return v, code


def test_confirm_happy_path(db, website):
    v, code = _start_with_known_code(website)
    confirmed = pvs.confirm(website=website, verification_id=str(v.id), code=code)
    assert confirmed.status == PhoneVerification.STATUS_VERIFIED


def test_confirm_wrong_code_increments_attempts(db, website):
    v, _ = _start_with_known_code(website)
    with pytest.raises(pvs.PhoneVerificationError, match="Incorrect"):
        pvs.confirm(website=website, verification_id=str(v.id), code="000000")
    v.refresh_from_db()
    assert v.attempts == 1
    assert v.status == PhoneVerification.STATUS_PENDING


def test_confirm_locks_after_max_attempts(db, website):
    v, _ = _start_with_known_code(website)
    for _ in range(v.max_attempts):
        with pytest.raises(pvs.PhoneVerificationError):
            pvs.confirm(website=website, verification_id=str(v.id), code="000000")
    v.refresh_from_db()
    # Next attempt — even with the right code — must be rejected.
    with pytest.raises(pvs.PhoneVerificationError, match="Too many"):
        pvs.confirm(website=website, verification_id=str(v.id), code="654321")
    v.refresh_from_db()
    assert v.status == PhoneVerification.STATUS_FAILED


def test_confirm_rejects_expired_code(db, website):
    v, code = _start_with_known_code(website)
    v.expires_at = timezone.now() - timedelta(seconds=1)
    v.save(update_fields=["expires_at"])
    with pytest.raises(pvs.PhoneVerificationError, match="expired"):
        pvs.confirm(website=website, verification_id=str(v.id), code=code)
    v.refresh_from_db()
    assert v.status == PhoneVerification.STATUS_EXPIRED


def test_confirm_rejects_unknown_id(db, website):
    with pytest.raises(pvs.PhoneVerificationError, match="not found"):
        pvs.confirm(
            website=website,
            verification_id="00000000-0000-0000-0000-000000000000",
            code="000000",
        )


def test_confirm_rejects_after_already_verified(db, website):
    v, code = _start_with_known_code(website)
    pvs.confirm(website=website, verification_id=str(v.id), code=code)
    with pytest.raises(pvs.PhoneVerificationError, match="no longer pending"):
        pvs.confirm(website=website, verification_id=str(v.id), code=code)


# ── consume() — the gate the PhoneNumber endpoint uses ────────────────────────


def test_consume_returns_verified_row(db, website):
    v, code = _start_with_known_code(website)
    pvs.confirm(website=website, verification_id=str(v.id), code=code)
    found = pvs.consume(website=website, verification_id=str(v.id), number=v.number)
    assert found is not None
    assert found.id == v.id


def test_consume_rejects_unverified(db, website):
    v, _ = _start_with_known_code(website)
    found = pvs.consume(website=website, verification_id=str(v.id), number=v.number)
    assert found is None


def test_consume_rejects_number_mismatch(db, website):
    v, code = _start_with_known_code(website)
    pvs.confirm(website=website, verification_id=str(v.id), code=code)
    found = pvs.consume(
        website=website, verification_id=str(v.id), number="+15555555555"
    )
    assert found is None


def test_consume_rejects_other_website(db, website, user):
    other = Website.objects.create(name="Other", url="https://other.test", user=user)
    v, code = _start_with_known_code(website)
    pvs.confirm(website=website, verification_id=str(v.id), code=code)
    assert pvs.consume(website=other, verification_id=str(v.id), number=v.number) is None


def test_consume_handles_blank_id(db, website):
    assert pvs.consume(website=website, verification_id="", number="+1") is None
