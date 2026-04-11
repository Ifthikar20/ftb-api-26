"""Tests for CallService — webhook processing, call listing, stats, and reminders.

These tests hit the service boundary directly, simulating the payloads that the
Retell webhook view and the internal LiveKit call-finish endpoint would send.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.voice_agent.models import CallbackReminder, CalendarEvent, CallLog
from apps.voice_agent.services.call_service import CallService
from apps.websites.models import Website
from core.exceptions import ResourceNotFound


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="owner@acme.test", password="x", full_name="Owner"
    )


@pytest.fixture
def website(db, user):
    return Website.objects.create(name="Acme", url="https://acme.test", user=user)


def _make_call(website, **overrides):
    defaults = dict(
        website=website,
        caller_phone="+12025550123",
        status=CallLog.STATUS_COMPLETED,
        direction=CallLog.DIRECTION_INBOUND,
        duration_seconds=120,
    )
    defaults.update(overrides)
    return CallLog.objects.create(**defaults)


# ── get_calls ────────────────────────────────────────────────────────────────


def test_get_calls_no_filter(db, website):
    _make_call(website)
    _make_call(website, direction=CallLog.DIRECTION_OUTBOUND)
    calls = CallService.get_calls(website.id)
    assert calls.count() == 2


def test_get_calls_filter_by_status(db, website):
    _make_call(website, status=CallLog.STATUS_COMPLETED)
    _make_call(website, status=CallLog.STATUS_MISSED)
    calls = CallService.get_calls(website.id, status=CallLog.STATUS_MISSED)
    assert calls.count() == 1
    assert calls.first().status == CallLog.STATUS_MISSED


def test_get_calls_filter_by_direction(db, website):
    _make_call(website, direction=CallLog.DIRECTION_INBOUND)
    _make_call(website, direction=CallLog.DIRECTION_OUTBOUND)
    calls = CallService.get_calls(website.id, direction=CallLog.DIRECTION_OUTBOUND)
    assert calls.count() == 1


def test_get_calls_filter_by_phone(db, website):
    _make_call(website, caller_phone="+12025550100")
    _make_call(website, caller_phone="+12025550200")
    calls = CallService.get_calls(website.id, phone="0100")
    assert calls.count() == 1


# ── get_call ─────────────────────────────────────────────────────────────────


def test_get_call_returns_existing(db, website):
    call = _make_call(website)
    result = CallService.get_call(website.id, call.id)
    assert result.id == call.id


def test_get_call_raises_not_found(db, website):
    import uuid

    with pytest.raises(ResourceNotFound):
        CallService.get_call(website.id, uuid.uuid4())


# ── process_call_started ─────────────────────────────────────────────────────


def test_process_call_started_creates_log(db, website):
    data = {
        "call_id": "ext_123",
        "direction": "inbound",
        "from_number": "+15559876543",
    }
    call = CallService.process_call_started(website.id, data)
    assert call.external_call_id == "ext_123"
    assert call.status == CallLog.STATUS_IN_PROGRESS
    assert call.caller_phone == "+15559876543"
    assert call.started_at is not None


def test_process_call_started_idempotent(db, website):
    data = {"call_id": "ext_456", "from_number": "+15550000001"}
    CallService.process_call_started(website.id, data)
    CallService.process_call_started(website.id, data)
    assert CallLog.objects.filter(external_call_id="ext_456").count() == 1


# ── process_call_ended ───────────────────────────────────────────────────────


def test_process_call_ended_updates_transcript(db, website, monkeypatch):
    # Prevent async extraction from firing
    monkeypatch.setattr(
        "apps.voice_agent.tasks.extract_call_data.delay",
        lambda *a, **kw: None,
    )
    data = {
        "call_id": "ext_end_1",
        "call": {
            "call_id": "ext_end_1",
            "transcript": "Agent: Hello.\nCaller: Hi!",
            "start_timestamp": 1000000,
            "end_timestamp": 1060000,
            "call_analysis": {
                "call_summary": "Brief greeting call",
                "user_sentiment": "positive",
                "call_intent": "inquiry",
                "custom_analysis_data": {"caller_name": "Bob"},
            },
        },
    }
    call = CallService.process_call_ended(website.id, data)
    assert call.status == CallLog.STATUS_COMPLETED
    assert "Hello" in call.transcript
    assert call.summary == "Brief greeting call"
    assert call.sentiment == "positive"
    assert call.duration_seconds == 60
    assert call.caller_name == "Bob"


def test_process_call_ended_handles_list_transcript(db, website, monkeypatch):
    monkeypatch.setattr(
        "apps.voice_agent.tasks.extract_call_data.delay",
        lambda *a, **kw: None,
    )
    data = {
        "call_id": "ext_end_2",
        "call": {
            "call_id": "ext_end_2",
            "transcript": [
                {"role": "agent", "content": "Hello!"},
                {"role": "user", "content": "Hi!"},
            ],
            "call_analysis": {},
        },
    }
    call = CallService.process_call_ended(website.id, data)
    assert "agent: Hello!" in call.transcript


# ── process_call_analyzed ────────────────────────────────────────────────────


def test_process_call_analyzed_merges_data(db, website):
    call = _make_call(
        website,
        external_call_id="ext_analyzed_1",
        extracted_data={"existing_key": "value"},
    )
    data = {
        "call_id": "ext_analyzed_1",
        "call_analysis": {
            "call_summary": "Updated summary",
            "user_sentiment": "frustrated",
            "custom_analysis_data": {"new_key": "new_value"},
        },
    }
    result = CallService.process_call_analyzed(website.id, data)
    assert result.summary == "Updated summary"
    assert result.sentiment == "frustrated"
    assert result.extracted_data["existing_key"] == "value"
    assert result.extracted_data["new_key"] == "new_value"


def test_process_call_analyzed_orphan_returns_none(db, website):
    data = {"call_id": "nonexistent", "call_analysis": {}}
    result = CallService.process_call_analyzed(website.id, data)
    assert result is None


# ── get_call_stats ───────────────────────────────────────────────────────────


def test_get_call_stats_empty(db, website):
    stats = CallService.get_call_stats(website.id)
    assert stats["total_calls"] == 0
    assert stats["total_duration"] == 0
    assert stats["appointments_booked"] == 0


def test_get_call_stats_aggregates(db, website):
    c1 = _make_call(website, duration_seconds=60, sentiment="positive")
    c2 = _make_call(website, duration_seconds=120, sentiment="positive", status=CallLog.STATUS_MISSED)
    _make_call(website, duration_seconds=180, direction=CallLog.DIRECTION_OUTBOUND)

    # Create an appointment linked to c1
    CalendarEvent.objects.create(
        website=website,
        call_log=c1,
        title="Test",
        attendee_name="X",
        attendee_phone="+10000000000",
        start_time=timezone.now(),
        end_time=timezone.now(),
    )

    stats = CallService.get_call_stats(website.id)
    assert stats["total_calls"] == 3
    assert stats["completed_calls"] == 2  # STATUS_COMPLETED
    assert stats["missed_calls"] == 1
    assert stats["inbound"] == 2
    assert stats["outbound"] == 1
    assert stats["total_duration"] == 360
    assert stats["appointments_booked"] == 1
    assert stats["sentiment"]["positive"] == 2


# ── Callback reminders ───────────────────────────────────────────────────────


def test_create_callback_reminder(db, website, user):
    now = timezone.now()
    reminder = CallService.create_callback_reminder(
        website_id=website.id,
        contact_name="Jane",
        contact_phone="+15550000001",
        remind_at=now,
        reason="Follow up on pricing",
        assigned_to=user,
    )
    assert reminder.pk is not None
    assert reminder.contact_name == "Jane"
    assert reminder.status == CallbackReminder.STATUS_PENDING
    assert reminder.assigned_to == user


def test_get_pending_reminders(db, website):
    CallbackReminder.objects.create(
        website=website,
        contact_name="Pending",
        contact_phone="+10000000001",
        remind_at=timezone.now(),
        status=CallbackReminder.STATUS_PENDING,
    )
    CallbackReminder.objects.create(
        website=website,
        contact_name="Completed",
        contact_phone="+10000000002",
        remind_at=timezone.now(),
        status=CallbackReminder.STATUS_COMPLETED,
    )
    reminders = CallService.get_pending_reminders(website.id)
    assert reminders.count() == 1
    assert reminders.first().contact_name == "Pending"


def test_complete_reminder(db, website):
    reminder = CallbackReminder.objects.create(
        website=website,
        contact_name="Test",
        contact_phone="+10000000003",
        remind_at=timezone.now(),
        status=CallbackReminder.STATUS_PENDING,
    )
    result = CallService.complete_reminder(reminder.id, website.id, notes="Called back")
    assert result.status == CallbackReminder.STATUS_COMPLETED
    assert result.notes == "Called back"


def test_dismiss_reminder(db, website):
    reminder = CallbackReminder.objects.create(
        website=website,
        contact_name="Test",
        contact_phone="+10000000004",
        remind_at=timezone.now(),
        status=CallbackReminder.STATUS_PENDING,
    )
    result = CallService.dismiss_reminder(reminder.id, website.id)
    assert result.status == CallbackReminder.STATUS_DISMISSED


def test_reminder_not_found_raises(db, website):
    import uuid

    with pytest.raises(ResourceNotFound):
        CallService.complete_reminder(uuid.uuid4(), website.id)
