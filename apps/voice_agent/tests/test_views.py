"""Integration tests for voice agent API views.

These tests exercise the full HTTP request cycle through DRF. Authentication
is handled via ``APIClient.force_authenticate``, matching the pattern used in
``test_context_document_api.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.voice_agent.models import (
    AgentConfig,
    AgentContextDocument,
    CalendarEvent,
    CallbackReminder,
    CallCampaign,
    CallLog,
    CallTarget,
    CallTodo,
    PhoneNumber,
)
from apps.websites.models import Website


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        email="owner@acme.test", password="pw12345!"
    )


@pytest.fixture
def website(db, user):
    site = Website.objects.create(name="Acme", url="https://acme.test", user=user)
    if hasattr(site, "owner_id"):
        site.owner = user
        site.save()
    return site


@pytest.fixture
def config(db, website):
    return AgentConfig.objects.create(
        website=website,
        is_active=True,
        business_name="Acme Inc",
        business_hours={
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
        },
    )


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _url(website_id, path):
    return f"/api/v1/voice-agent/{website_id}/{path}"


# ── Agent Config ─────────────────────────────────────────────────────────────


class TestAgentConfig:
    def test_get_config_creates_default(self, client, website):
        res = client.get(_url(website.id, "config/"))
        assert res.status_code == 200
        assert res.data["is_active"] is True
        assert AgentConfig.objects.filter(website=website).exists()

    def test_get_config_returns_existing(self, client, website, config):
        res = client.get(_url(website.id, "config/"))
        assert res.status_code == 200
        assert res.data["business_name"] == "Acme Inc"

    def test_put_config_updates(self, client, website, config):
        res = client.put(
            _url(website.id, "config/"),
            {"business_name": "New Name", "timezone": "US/Eastern"},
            format="json",
        )
        assert res.status_code == 200
        config.refresh_from_db()
        assert config.business_name == "New Name"
        assert config.timezone == "US/Eastern"

    def test_unauthenticated_rejected(self, website):
        c = APIClient()
        res = c.get(_url(website.id, "config/"))
        assert res.status_code in (401, 403)


# ── Call Logs ────────────────────────────────────────────────────────────────


class TestCallLogs:
    @pytest.fixture(autouse=True)
    def _setup(self, website):
        self.call1 = CallLog.objects.create(
            website=website,
            caller_phone="+12025550100",
            status=CallLog.STATUS_COMPLETED,
            direction=CallLog.DIRECTION_INBOUND,
            duration_seconds=60,
            sentiment="positive",
        )
        self.call2 = CallLog.objects.create(
            website=website,
            caller_phone="+12025550200",
            status=CallLog.STATUS_MISSED,
            direction=CallLog.DIRECTION_OUTBOUND,
            duration_seconds=0,
        )

    def test_list_calls(self, client, website):
        res = client.get(_url(website.id, "calls/"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 2

    def test_list_calls_filter_status(self, client, website):
        res = client.get(_url(website.id, "calls/?status=missed"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 1

    def test_list_calls_filter_direction(self, client, website):
        res = client.get(_url(website.id, "calls/?direction=outbound"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 1

    def test_call_detail(self, client, website):
        res = client.get(_url(website.id, f"calls/{self.call1.id}/"))
        assert res.status_code == 200
        assert res.data["caller_phone"] == "+12025550100"

    def test_call_stats(self, client, website):
        res = client.get(_url(website.id, "calls/stats/"))
        assert res.status_code == 200
        assert res.data["total_calls"] == 2
        assert res.data["completed_calls"] == 1
        assert res.data["missed_calls"] == 1


# ── Calendar / Appointments ──────────────────────────────────────────────────


class TestCalendar:
    def test_list_events(self, client, website, config):
        now = timezone.now()
        CalendarEvent.objects.create(
            website=website,
            title="Future",
            attendee_name="Alice",
            attendee_phone="+10000000001",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, minutes=30),
            status=CalendarEvent.STATUS_SCHEDULED,
        )
        res = client.get(_url(website.id, "calendar/"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 1

    def test_create_event(self, client, website, config):
        start = timezone.now() + timedelta(days=3)
        end = start + timedelta(minutes=30)
        res = client.post(
            _url(website.id, "calendar/"),
            {
                "attendee_name": "Bob",
                "attendee_phone": "+15559876543",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            format="json",
        )
        assert res.status_code == 201
        assert res.data["attendee_name"] == "Bob"
        assert CalendarEvent.objects.filter(website=website).count() == 1

    def test_availability_requires_date(self, client, website, config):
        res = client.get(_url(website.id, "calendar/availability/"))
        assert res.status_code == 400

    def test_availability_returns_slots(self, client, website, config):
        # Pick next Monday
        today = timezone.now().date()
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        monday = today + timedelta(days=days_ahead)
        res = client.get(_url(website.id, f"calendar/availability/?date={monday}"))
        assert res.status_code == 200
        assert len(res.data["available_slots"]) > 0


# ── Todos ────────────────────────────────────────────────────────────────────


class TestTodos:
    def test_list_todos(self, client, website):
        call = CallLog.objects.create(
            website=website, caller_phone="+10000000000",
            status=CallLog.STATUS_COMPLETED,
        )
        CallTodo.objects.create(
            website=website, call_log=call,
            description="Follow up", priority="high",
        )
        res = client.get(_url(website.id, "todos/"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 1

    def test_update_todo(self, client, website):
        call = CallLog.objects.create(
            website=website, caller_phone="+10000000000",
            status=CallLog.STATUS_COMPLETED,
        )
        todo = CallTodo.objects.create(
            website=website, call_log=call,
            description="Task", status="open",
        )
        res = client.put(
            _url(website.id, f"todos/{todo.id}/"),
            {"status": "done"},
            format="json",
        )
        assert res.status_code == 200
        todo.refresh_from_db()
        assert todo.status == "done"
        assert todo.completed_at is not None

    def test_todo_stats(self, client, website):
        call = CallLog.objects.create(
            website=website, caller_phone="+10000000000",
            status=CallLog.STATUS_COMPLETED,
        )
        CallTodo.objects.create(website=website, call_log=call, description="A", status="open")
        CallTodo.objects.create(website=website, call_log=call, description="B", status="done")
        res = client.get(_url(website.id, "todos/stats/"))
        assert res.status_code == 200
        assert res.data["total"] == 2
        assert res.data["open"] == 1
        assert res.data["done"] == 1


# ── Reminders ────────────────────────────────────────────────────────────────


class TestReminders:
    def test_list_pending_reminders(self, client, website):
        CallbackReminder.objects.create(
            website=website,
            contact_name="Jane",
            contact_phone="+10000000001",
            remind_at=timezone.now() + timedelta(hours=1),
            status=CallbackReminder.STATUS_PENDING,
        )
        res = client.get(_url(website.id, "reminders/"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 1

    def test_create_reminder(self, client, website):
        remind_at = (timezone.now() + timedelta(hours=2)).isoformat()
        res = client.post(
            _url(website.id, "reminders/"),
            {
                "contact_name": "Bob",
                "contact_phone": "+15551234567",
                "remind_at": remind_at,
                "reason": "Follow up on pricing",
            },
            format="json",
        )
        assert res.status_code == 201
        assert res.data["contact_name"] == "Bob"

    def test_complete_reminder(self, client, website):
        reminder = CallbackReminder.objects.create(
            website=website,
            contact_name="Eve",
            contact_phone="+10000000002",
            remind_at=timezone.now(),
            status=CallbackReminder.STATUS_PENDING,
        )
        res = client.put(
            _url(website.id, f"reminders/{reminder.id}/"),
            {"action": "complete", "notes": "Called back successfully"},
            format="json",
        )
        assert res.status_code == 200
        reminder.refresh_from_db()
        assert reminder.status == CallbackReminder.STATUS_COMPLETED

    def test_dismiss_reminder(self, client, website):
        reminder = CallbackReminder.objects.create(
            website=website,
            contact_name="Frank",
            contact_phone="+10000000003",
            remind_at=timezone.now(),
            status=CallbackReminder.STATUS_PENDING,
        )
        res = client.put(
            _url(website.id, f"reminders/{reminder.id}/"),
            {"action": "dismiss"},
            format="json",
        )
        assert res.status_code == 200
        reminder.refresh_from_db()
        assert reminder.status == CallbackReminder.STATUS_DISMISSED


# ── Phone Numbers ────────────────────────────────────────────────────────────


class TestPhoneNumbers:
    def test_list_phone_numbers(self, client, website):
        PhoneNumber.objects.create(
            website=website, number="+15550000001", provider="telnyx",
            is_verified=True,
        )
        res = client.get(_url(website.id, "phone-numbers/"))
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_update_phone_number(self, client, website):
        num = PhoneNumber.objects.create(
            website=website, number="+15550000002", provider="telnyx",
            label="Old", is_verified=True,
        )
        res = client.put(
            _url(website.id, f"phone-numbers/{num.id}/"),
            {"label": "Main Line"},
            format="json",
        )
        assert res.status_code == 200
        num.refresh_from_db()
        assert num.label == "Main Line"

    def test_delete_phone_number(self, client, website):
        num = PhoneNumber.objects.create(
            website=website, number="+15550000003", provider="telnyx",
            is_verified=True,
        )
        res = client.delete(_url(website.id, f"phone-numbers/{num.id}/"))
        assert res.status_code == 204
        assert not PhoneNumber.objects.filter(id=num.id).exists()


# ── Lead Detection ───────────────────────────────────────────────────────────


class TestLeadDetection:
    def test_list_possible_leads(self, client, website):
        CallLog.objects.create(
            website=website, caller_phone="+12025550100",
            status=CallLog.STATUS_COMPLETED,
            is_possible_lead=True, lead_score=80,
        )
        CallLog.objects.create(
            website=website, caller_phone="+12025550200",
            status=CallLog.STATUS_COMPLETED,
            is_possible_lead=False,
        )
        res = client.get(_url(website.id, "lead-detection/"))
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 1

    def test_dismiss_possible_lead(self, client, website):
        call = CallLog.objects.create(
            website=website, caller_phone="+12025550100",
            status=CallLog.STATUS_COMPLETED,
            is_possible_lead=True, lead_score=80,
        )
        res = client.post(
            _url(website.id, f"lead-detection/{call.id}/"),
            {"action": "dismiss"},
            format="json",
        )
        assert res.status_code == 200
        call.refresh_from_db()
        assert call.is_possible_lead is False
        assert call.lead_dismissed_at is not None


# ── Usage ────────────────────────────────────────────────────────────────────


class TestUsage:
    def test_get_usage_empty(self, client, website):
        res = client.get(_url(website.id, "usage/"))
        assert res.status_code == 200
        assert res.data["current_period"]["total_calls"] == 0

    def test_get_usage_with_months_param(self, client, website):
        res = client.get(_url(website.id, "usage/?months=3"))
        assert res.status_code == 200
        assert "history" in res.data


# ── Onboarding ───────────────────────────────────────────────────────────────


class TestOnboarding:
    def test_list_templates(self, client, website):
        res = client.get("/api/v1/voice-agent/onboarding/templates/")
        assert res.status_code == 200
        assert isinstance(res.data, list)
        assert len(res.data) > 0

    def test_setup_status(self, client, website, config):
        res = client.get(_url(website.id, "onboarding/setup-status/"))
        assert res.status_code == 200
        assert "inbound" in res.data
        assert "outbound" in res.data
