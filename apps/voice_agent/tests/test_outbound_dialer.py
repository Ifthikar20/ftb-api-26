"""Tests for the outbound dialer Celery tasks."""

from unittest.mock import MagicMock, patch

import pytest

from apps.voice_agent.models import (
    CallCampaign,
    CallLog,
    CallTarget,
    DoNotCallEntry,
    PhoneNumber,
)
from apps.voice_agent.tasks import dispatch_campaign, place_outbound_call
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
def from_number(db, website):
    return PhoneNumber.objects.create(
        website=website,
        number="+15550000000",
        provider=PhoneNumber.PROVIDER_TELNYX,
        livekit_outbound_trunk_id="trunk_abc",
    )


@pytest.fixture
def campaign(db, website, from_number):
    return CallCampaign.objects.create(
        website=website,
        name="Q2 outreach",
        welcome_message="Hi! This is a quick call about our new offer.",
        from_number=from_number,
        status=CallCampaign.STATUS_RUNNING,
        respect_business_hours=False,
        calls_per_minute=5,
    )


@pytest.fixture
def target(db, campaign):
    return CallTarget.objects.create(campaign=campaign, phone="+15551234567", name="Bob")


def test_place_outbound_call_skips_dnc(target):
    DoNotCallEntry.objects.create(phone=target.phone)
    out = place_outbound_call(str(target.id))
    assert out["status"] == "dnc"
    target.refresh_from_db()
    assert target.status == CallTarget.STATUS_DO_NOT_CALL
    assert CallLog.objects.count() == 0


def test_place_outbound_call_fails_without_trunk(target, from_number):
    from_number.livekit_outbound_trunk_id = ""
    from_number.save()
    out = place_outbound_call(str(target.id))
    assert out["status"] == "no_trunk"
    target.refresh_from_db()
    assert target.status == CallTarget.STATUS_FAILED


def test_place_outbound_call_dispatches_to_livekit(target):
    with patch(
        "apps.voice_agent.services.livekit_service.LiveKitService.create_room",
        return_value=MagicMock(),
    ) as mock_room, patch(
        "apps.voice_agent.services.livekit_service.LiveKitService.dispatch_agent",
        return_value=MagicMock(),
    ) as mock_dispatch, patch(
        "apps.voice_agent.services.livekit_service.LiveKitService.create_sip_participant",
        return_value=MagicMock(),
    ) as mock_sip:
        out = place_outbound_call(str(target.id))

    assert out["status"] == "dialing"
    mock_room.assert_called_once()
    mock_dispatch.assert_called_once()
    mock_sip.assert_called_once()
    target.refresh_from_db()
    assert target.status == CallTarget.STATUS_DIALING
    assert target.attempt_count == 1
    log = CallLog.objects.get(target=target)
    assert log.direction == CallLog.DIRECTION_OUTBOUND
    assert log.status == CallLog.STATUS_RINGING
    assert log.external_call_id.startswith("voice-agent-out-")


def test_dispatch_campaign_marks_targets_queued(campaign, target):
    with patch(
        "apps.voice_agent.tasks.place_outbound_call.apply_async"
    ) as mock_apply:
        out = dispatch_campaign(str(campaign.id))

    assert out["status"] == "ok"
    assert out["queued"] == 1
    mock_apply.assert_called_once()
    target.refresh_from_db()
    assert target.status == CallTarget.STATUS_QUEUED


def test_dispatch_campaign_completes_when_no_pending(campaign):
    out = dispatch_campaign(str(campaign.id))
    assert out["queued"] == 0
    campaign.refresh_from_db()
    assert campaign.status == CallCampaign.STATUS_COMPLETED


def test_dispatch_campaign_skipped_when_paused(campaign, target):
    campaign.status = CallCampaign.STATUS_PAUSED
    campaign.save()
    out = dispatch_campaign(str(campaign.id))
    assert out["status"] == CallCampaign.STATUS_PAUSED
    target.refresh_from_db()
    assert target.status == CallTarget.STATUS_PENDING
