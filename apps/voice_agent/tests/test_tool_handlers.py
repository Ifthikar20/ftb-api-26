"""Tests for the shared tool_handlers module used by Retell webhook + LiveKit worker."""

from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.voice_agent.services import tool_handlers
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


# Tool handlers fall back to a default 30-minute appointment when no AgentConfig
# row exists, so the tests don't create one (avoids touching unrelated schema).
@pytest.fixture
def config(website):
    return website


def test_check_availability_missing_date():
    out = tool_handlers.check_availability("00000000-0000-0000-0000-000000000000", {})
    assert "valid date" in out["result"].lower()


def test_check_availability_returns_slots(config):
    fake_slots = [{"start": "09:00", "end": "09:30"}]
    with patch(
        "apps.voice_agent.services.tool_handlers.CalendarService.get_available_slots",
        return_value=fake_slots,
    ):
        out = tool_handlers.check_availability(
            str(config.id), {"date": date.today().isoformat()}
        )
    assert "09:00-09:30" in out["result"]


def test_schedule_appointment_requires_date_and_time(config):
    out = tool_handlers.schedule_appointment(
        str(config.id), {"attendee_name": "Bob"}
    )
    assert "date and time" in out["result"].lower()


def test_schedule_appointment_books(config):
    args = {
        "attendee_name": "Bob",
        "attendee_phone": "+15551234567",
        "preferred_date": (date.today() + timedelta(days=1)).isoformat(),
        "preferred_time": "10:00",
        "reason": "consult",
    }

    class _FakeEvent:
        id = "11111111-1111-1111-1111-111111111111"

    with patch(
        "apps.voice_agent.services.tool_handlers.CalendarService.book_appointment",
        return_value=_FakeEvent(),
    ) as mock_book, patch(
        "apps.voice_agent.tasks.sync_calendar_event"
    ) as mock_task:
        mock_task.delay.return_value = None
        out = tool_handlers.schedule_appointment(str(config.id), args)

    mock_book.assert_called_once()
    assert "booked for Bob" in out["result"]


def test_request_callback_creates_reminder(config):
    class _FakeReminder:
        id = "22222222-2222-2222-2222-222222222222"

    with patch(
        "apps.voice_agent.services.tool_handlers.CallService.create_callback_reminder",
        return_value=_FakeReminder(),
    ) as mock_create, patch(
        "apps.voice_agent.tasks.send_callback_notification"
    ) as mock_task:
        mock_task.delay.return_value = None
        out = tool_handlers.request_callback(
            str(config.id),
            {"contact_name": "Alice", "contact_phone": "+15551112222"},
        )

    mock_create.assert_called_once()
    assert "Alice" in out["result"]
