"""Tests for CalendarService — availability, booking, conflicts, and cancellation.

These tests exercise the service boundary without touching any external calendar
API. Google Calendar syncs are triggered via Celery tasks that are not invoked here.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from apps.voice_agent.models import AgentConfig, CalendarEvent
from apps.voice_agent.services.calendar_service import CalendarService
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
def config(db, website):
    return AgentConfig.objects.create(
        website=website,
        appointment_duration_minutes=30,
        business_hours={
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
        },
    )


def _next_weekday(weekday: int) -> date:
    """Return the next date that falls on ``weekday`` (0=Monday)."""
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


# ── get_available_slots ──────────────────────────────────────────────────────


def test_slots_returned_for_business_day(config):
    """A Monday with no bookings should return 16 thirty-minute slots (09:00-17:00)."""
    monday = _next_weekday(0)
    slots = CalendarService.get_available_slots(website_id=config.website_id, date=monday)
    assert len(slots) == 16
    assert slots[0] == {"start": "09:00", "end": "09:30"}
    assert slots[-1] == {"start": "16:30", "end": "17:00"}


def test_slots_empty_for_weekend(config):
    """Saturday has no business hours configured — should return empty."""
    saturday = _next_weekday(5)
    slots = CalendarService.get_available_slots(website_id=config.website_id, date=saturday)
    assert slots == []


def test_slots_exclude_booked_times(config):
    """An existing appointment at 10:00-10:30 should remove that slot."""
    monday = _next_weekday(0)
    CalendarEvent.objects.create(
        website=config.website,
        title="Existing",
        attendee_name="Alice",
        attendee_phone="+10000000000",
        start_time=timezone.make_aware(datetime.combine(monday, datetime.min.time().replace(hour=10))),
        end_time=timezone.make_aware(datetime.combine(monday, datetime.min.time().replace(hour=10, minute=30))),
        status=CalendarEvent.STATUS_SCHEDULED,
    )
    slots = CalendarService.get_available_slots(website_id=config.website_id, date=monday)
    starts = [s["start"] for s in slots]
    assert "10:00" not in starts
    assert "09:30" in starts  # Adjacent slot is still available


def test_slots_respect_custom_duration(config):
    """60-minute duration should yield 8 slots for an 8-hour day."""
    monday = _next_weekday(0)
    config.appointment_duration_minutes = 60
    config.save()
    slots = CalendarService.get_available_slots(website_id=config.website_id, date=monday)
    assert len(slots) == 8


def test_slots_empty_when_no_config(website):
    """No AgentConfig means no business hours — return empty."""
    monday = _next_weekday(0)
    slots = CalendarService.get_available_slots(website_id=website.id, date=monday)
    assert slots == []


# ── book_appointment ─────────────────────────────────────────────────────────


def test_book_creates_event(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=10))
    )
    event = CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="Bob",
        attendee_phone="+15551234567",
        start_time=start,
    )
    assert event.pk is not None
    assert event.attendee_name == "Bob"
    assert event.status == CalendarEvent.STATUS_SCHEDULED
    assert event.title == "Appointment with Bob"
    # Auto-computed end time from config duration
    assert event.end_time == start + timedelta(minutes=30)


def test_book_with_explicit_end_time(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=14))
    )
    end = start + timedelta(minutes=60)
    event = CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="Carol",
        attendee_phone="+15559876543",
        start_time=start,
        end_time=end,
    )
    assert event.end_time == end


def test_book_rejects_conflict(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=11))
    )
    CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="First",
        attendee_phone="+15550000001",
        start_time=start,
    )
    with pytest.raises(ValueError, match="already booked"):
        CalendarService.book_appointment(
            website_id=config.website_id,
            attendee_name="Second",
            attendee_phone="+15550000002",
            start_time=start,
        )


def test_book_raises_without_config(website):
    start = timezone.make_aware(datetime(2026, 6, 1, 10, 0))
    with pytest.raises(ValueError, match="not configured"):
        CalendarService.book_appointment(
            website_id=website.id,
            attendee_name="Nobody",
            attendee_phone="+15550000000",
            start_time=start,
        )


# ── cancel_appointment ───────────────────────────────────────────────────────


def test_cancel_sets_status(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=9))
    )
    event = CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="Dave",
        attendee_phone="+15550000003",
        start_time=start,
    )
    result = CalendarService.cancel_appointment(event.id, config.website_id)
    assert result.status == CalendarEvent.STATUS_CANCELLED


def test_cancel_already_cancelled_raises(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=15))
    )
    event = CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="Eve",
        attendee_phone="+15550000004",
        start_time=start,
    )
    CalendarService.cancel_appointment(event.id, config.website_id)
    with pytest.raises(ValueError, match="already"):
        CalendarService.cancel_appointment(event.id, config.website_id)


# ── update_status ────────────────────────────────────────────────────────────


def test_update_status_valid(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=13))
    )
    event = CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="Frank",
        attendee_phone="+15550000005",
        start_time=start,
    )
    result = CalendarService.update_status(event.id, config.website_id, CalendarEvent.STATUS_CONFIRMED)
    assert result.status == CalendarEvent.STATUS_CONFIRMED


def test_update_status_invalid_raises(config):
    monday = _next_weekday(0)
    start = timezone.make_aware(
        datetime.combine(monday, datetime.min.time().replace(hour=14))
    )
    event = CalendarService.book_appointment(
        website_id=config.website_id,
        attendee_name="Grace",
        attendee_phone="+15550000006",
        start_time=start,
    )
    with pytest.raises(ValueError, match="Invalid status"):
        CalendarService.update_status(event.id, config.website_id, "bogus")


# ── get_upcoming ─────────────────────────────────────────────────────────────


def test_get_upcoming_returns_future_only(config):
    now = timezone.now()
    # Past event — should not appear
    CalendarEvent.objects.create(
        website=config.website,
        title="Past",
        attendee_name="Old",
        attendee_phone="+10000000000",
        start_time=now - timedelta(days=2),
        end_time=now - timedelta(days=2, minutes=-30),
        status=CalendarEvent.STATUS_SCHEDULED,
    )
    # Future event — should appear
    CalendarEvent.objects.create(
        website=config.website,
        title="Future",
        attendee_name="New",
        attendee_phone="+10000000001",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, minutes=30),
        status=CalendarEvent.STATUS_SCHEDULED,
    )
    upcoming = CalendarService.get_upcoming(config.website_id, days=30)
    assert upcoming.count() == 1
    assert upcoming.first().title == "Future"


def test_get_upcoming_excludes_cancelled(config):
    now = timezone.now()
    CalendarEvent.objects.create(
        website=config.website,
        title="Cancelled",
        attendee_name="Gone",
        attendee_phone="+10000000002",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, minutes=30),
        status=CalendarEvent.STATUS_CANCELLED,
    )
    upcoming = CalendarService.get_upcoming(config.website_id, days=30)
    assert upcoming.count() == 0
