"""Tests for ExtractionService — post-call transcript extraction and todo management.

The LLM call is mocked so these tests run without network access. We verify
that the service correctly parses the structured response, creates the right
database records, and handles failures gracefully.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.voice_agent.models import CallExtraction, CallLog, CallTodo
from apps.voice_agent.services.extraction_service import ExtractionService
from apps.websites.models import Website
from core.exceptions import ResourceNotFound

MOCK_EXTRACTION = {
    "caller_info": {
        "name": "Jane Smith",
        "phone": "+12025551234",
        "email": "jane@acme.com",
        "company": "Acme Corp",
    },
    "call_summary": "Caller inquired about premium plan pricing and wants a demo.",
    "call_category": "sales",
    "sentiment": "positive",
    "action_items": [
        {
            "description": "Send premium plan pricing sheet",
            "priority": "high",
            "due_date": "2026-04-15",
        },
        {
            "description": "Schedule demo with engineering team",
            "priority": "medium",
        },
    ],
    "appointments": [
        {
            "date": "2026-04-15",
            "time": "14:00",
            "description": "Product demo",
            "confirmed": False,
        },
    ],
    "follow_ups": [
        {"description": "Send pricing to jane@acme.com", "urgency": "immediate"},
        {"description": "Check back next week", "urgency": "this_week"},
    ],
}


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
def call_with_transcript(db, website):
    return CallLog.objects.create(
        website=website,
        caller_phone="+12025551234",
        status=CallLog.STATUS_COMPLETED,
        direction=CallLog.DIRECTION_INBOUND,
        duration_seconds=180,
        transcript=(
            "Agent: Hello! Thank you for calling Acme. How can I help?\n"
            "Caller: Hi, I'm Jane Smith from Acme Corp. I'd like to know "
            "about your premium plan pricing.\n"
            "Agent: Of course! I can send that over. What's your email?\n"
            "Caller: jane@acme.com\n"
            "Agent: Got it. Would you also like to schedule a demo?\n"
            "Caller: Yes, how about next Tuesday at 2pm?\n"
            "Agent: Perfect, I'll set that up."
        ),
    )


@pytest.fixture
def call_no_transcript(db, website):
    return CallLog.objects.create(
        website=website,
        caller_phone="+12025559999",
        status=CallLog.STATUS_MISSED,
        direction=CallLog.DIRECTION_INBOUND,
        duration_seconds=0,
    )


def _mock_selfhosted_extract(prompt, schema):
    return {"data": MOCK_EXTRACTION, "model": "qwen-7b-awq (test)"}


# ── extract_from_transcript ──────────────────────────────────────────────────


def test_extraction_creates_records(call_with_transcript, monkeypatch):
    """Full extraction creates CallExtraction + CallTodo records."""
    monkeypatch.setattr(
        "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json",
        _mock_selfhosted_extract,
    )
    # Prevent lead scoring from running (tested separately)
    monkeypatch.setattr(
        "apps.voice_agent.services.lead_scoring_service.score_call",
        lambda *a, **kw: None,
    )

    extraction = ExtractionService.extract_from_transcript(call_with_transcript)
    assert extraction is not None
    assert extraction.call_summary == MOCK_EXTRACTION["call_summary"]
    assert extraction.call_category == "sales"
    assert extraction.sentiment == "positive"
    assert extraction.model_used == "qwen-7b-awq (test)"
    assert extraction.processing_time_ms >= 0

    # Should have created 4 todos: 2 action items + 2 follow-ups
    todos = CallTodo.objects.filter(call_log=call_with_transcript)
    assert todos.count() == 4

    # Verify the high-priority action item
    high = todos.filter(priority="high").first()
    assert high is not None
    assert "pricing sheet" in high.description

    # Verify the follow-up todo
    followup = todos.filter(description__startswith="Follow-up:").first()
    assert followup is not None


def test_extraction_updates_caller_info_on_call_log(call_with_transcript, monkeypatch):
    """Extracted caller info should back-fill empty fields on CallLog."""
    monkeypatch.setattr(
        "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json",
        _mock_selfhosted_extract,
    )
    monkeypatch.setattr(
        "apps.voice_agent.services.lead_scoring_service.score_call",
        lambda *a, **kw: None,
    )
    ExtractionService.extract_from_transcript(call_with_transcript)

    call_with_transcript.refresh_from_db()
    assert call_with_transcript.caller_name == "Jane Smith"
    assert call_with_transcript.caller_email == "jane@acme.com"
    assert call_with_transcript.caller_company == "Acme Corp"
    assert call_with_transcript.summary == MOCK_EXTRACTION["call_summary"]
    assert call_with_transcript.call_intent == "sales"


def test_extraction_skips_no_transcript(call_no_transcript):
    """Calls without a transcript should return None and create nothing."""
    result = ExtractionService.extract_from_transcript(call_no_transcript)
    assert result is None
    assert CallExtraction.objects.count() == 0
    assert CallTodo.objects.count() == 0


def test_extraction_falls_back_to_openai(call_with_transcript, monkeypatch):
    """When self-hosted LLM fails, should fall back to OpenAI."""
    # Make self-hosted fail
    monkeypatch.setattr(
        "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json",
        lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("GPU offline")),
    )
    # Mock the OpenAI fallback
    monkeypatch.setattr(
        "apps.voice_agent.services.extraction_service.ExtractionService._fallback_openai_extract",
        lambda self_or_prompt, *a: MOCK_EXTRACTION,
    )
    monkeypatch.setattr(
        "apps.voice_agent.services.lead_scoring_service.score_call",
        lambda *a, **kw: None,
    )
    extraction = ExtractionService.extract_from_transcript(call_with_transcript)
    assert extraction is not None
    assert extraction.model_used == "gpt-4o-mini (fallback)"


def test_extraction_returns_none_when_all_fail(call_with_transcript, monkeypatch):
    """When both LLMs fail, extraction returns None without crashing."""
    monkeypatch.setattr(
        "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json",
        lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("GPU offline")),
    )
    monkeypatch.setattr(
        "apps.voice_agent.services.extraction_service.ExtractionService._fallback_openai_extract",
        lambda self_or_prompt, *a: (_ for _ in ()).throw(RuntimeError("No API key")),
    )
    result = ExtractionService.extract_from_transcript(call_with_transcript)
    assert result is None


def test_extraction_does_not_overwrite_existing_caller_info(call_with_transcript, monkeypatch):
    """If CallLog already has caller info, extraction should not overwrite it."""
    call_with_transcript.caller_name = "Pre-filled Name"
    call_with_transcript.save(update_fields=["caller_name"])

    monkeypatch.setattr(
        "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json",
        _mock_selfhosted_extract,
    )
    monkeypatch.setattr(
        "apps.voice_agent.services.lead_scoring_service.score_call",
        lambda *a, **kw: None,
    )
    ExtractionService.extract_from_transcript(call_with_transcript)
    call_with_transcript.refresh_from_db()
    assert call_with_transcript.caller_name == "Pre-filled Name"


# ── get_todos ────────────────────────────────────────────────────────────────


def test_get_todos_no_filter(db, website):
    call = CallLog.objects.create(
        website=website, caller_phone="+10000000000",
        status=CallLog.STATUS_COMPLETED,
    )
    CallTodo.objects.create(website=website, call_log=call, description="A", priority="high")
    CallTodo.objects.create(website=website, call_log=call, description="B", priority="low")
    todos = ExtractionService.get_todos(website.id)
    assert todos.count() == 2


def test_get_todos_filter_by_status(db, website):
    call = CallLog.objects.create(
        website=website, caller_phone="+10000000000",
        status=CallLog.STATUS_COMPLETED,
    )
    CallTodo.objects.create(website=website, call_log=call, description="Open", status="open")
    CallTodo.objects.create(website=website, call_log=call, description="Done", status="done")
    todos = ExtractionService.get_todos(website.id, status="open")
    assert todos.count() == 1


def test_get_todos_filter_by_priority(db, website):
    call = CallLog.objects.create(
        website=website, caller_phone="+10000000000",
        status=CallLog.STATUS_COMPLETED,
    )
    CallTodo.objects.create(website=website, call_log=call, description="H", priority="high")
    CallTodo.objects.create(website=website, call_log=call, description="L", priority="low")
    todos = ExtractionService.get_todos(website.id, priority="high")
    assert todos.count() == 1


# ── update_todo ──────────────────────────────────────────────────────────────


def test_update_todo_status(db, website):
    call = CallLog.objects.create(
        website=website, caller_phone="+10000000000",
        status=CallLog.STATUS_COMPLETED,
    )
    todo = CallTodo.objects.create(
        website=website, call_log=call, description="Task", status="open"
    )
    result = ExtractionService.update_todo(todo.id, website.id, status="in_progress")
    assert result.status == "in_progress"
    assert result.completed_at is None


def test_update_todo_done_sets_completed_at(db, website):
    call = CallLog.objects.create(
        website=website, caller_phone="+10000000000",
        status=CallLog.STATUS_COMPLETED,
    )
    todo = CallTodo.objects.create(
        website=website, call_log=call, description="Task", status="open"
    )
    result = ExtractionService.update_todo(todo.id, website.id, status="done")
    assert result.status == "done"
    assert result.completed_at is not None


def test_update_todo_not_found_raises(db, website):
    import uuid

    with pytest.raises(ResourceNotFound):
        ExtractionService.update_todo(uuid.uuid4(), website.id, status="done")


# ── get_todo_stats ───────────────────────────────────────────────────────────


def test_get_todo_stats(db, website):
    call = CallLog.objects.create(
        website=website, caller_phone="+10000000000",
        status=CallLog.STATUS_COMPLETED,
    )
    CallTodo.objects.create(website=website, call_log=call, description="A", status="open", priority="high")
    CallTodo.objects.create(website=website, call_log=call, description="B", status="in_progress", priority="medium")
    CallTodo.objects.create(website=website, call_log=call, description="C", status="done", priority="low")

    stats = ExtractionService.get_todo_stats(website.id)
    assert stats["total"] == 3
    assert stats["open"] == 1
    assert stats["in_progress"] == 1
    assert stats["done"] == 1
    assert stats["high_priority"] == 1
