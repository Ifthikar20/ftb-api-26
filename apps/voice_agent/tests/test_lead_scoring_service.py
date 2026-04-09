"""Tests for the transcript-based lead scoring service.

These tests intentionally avoid the LLM and the extraction pipeline — the
scorer must be a pure function of (CallLog state, extraction dict). Each
test exercises a single signal in isolation so weight changes are easy to
spot in the diff. The integration with ``ExtractionService`` is covered
indirectly by ``test_outbound_dialer`` and is not duplicated here.
"""

from __future__ import annotations

import pytest

from apps.voice_agent.models import CallLog
from apps.voice_agent.services import lead_scoring_service as lss
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


def _make_call(website, **overrides):
    """Default to a 'real conversation' that scores zero on its own."""
    defaults = dict(
        website=website,
        caller_phone="+12025550123",
        status=CallLog.STATUS_COMPLETED,
        direction=CallLog.DIRECTION_INBOUND,
        duration_seconds=120,
        transcript="hello, just calling to say hi",
    )
    defaults.update(overrides)
    return CallLog.objects.create(**defaults)


# ── Individual signal tests ────────────────────────────────────────────────────


def test_short_call_never_qualifies(db, website):
    """A 10-second call cannot be a lead even if every other signal fires."""
    call = _make_call(
        website,
        duration_seconds=10,
        caller_email="hot@lead.com",
        caller_company="BigCorp",
        call_intent="sales",
        sentiment="positive",
        transcript="i want to buy your product",
    )
    lss.score_call(call, extraction_data={})
    call.refresh_from_db()
    assert call.is_possible_lead is False
    assert "real_conversation" not in call.lead_signals


def test_email_signal(db, website):
    call = _make_call(website, caller_email="x@y.com")
    lss.score_call(call, extraction_data={})
    assert call.lead_signals.get("shared_email") == 20
    # 20 (email) + 5 (real_conversation) = 25, below threshold
    assert call.is_possible_lead is False


def test_company_signal(db, website):
    call = _make_call(website, caller_company="Acme Corp")
    lss.score_call(call, extraction_data={})
    assert call.lead_signals.get("shared_company") == 15


def test_intent_signal_fires_for_sales(db, website):
    call = _make_call(website, call_intent="sales")
    lss.score_call(call, extraction_data={})
    assert call.lead_signals.get("intent_sales") == 25


def test_intent_signal_skipped_for_complaint(db, website):
    call = _make_call(website, call_intent="complaint")
    lss.score_call(call, extraction_data={})
    # Only the real_conversation gate should fire.
    assert set(call.lead_signals.keys()) == {"real_conversation"}


def test_sentiment_signal(db, website):
    call = _make_call(website, sentiment="positive")
    lss.score_call(call, extraction_data={})
    assert call.lead_signals.get("positive_sentiment") == 10


def test_appointment_discussed_signal(db, website):
    call = _make_call(website)
    lss.score_call(
        call,
        extraction_data={"appointments_detected": [{"date": "tomorrow", "time": "10am"}]},
    )
    assert call.lead_signals.get("appointment_discussed") == 20


def test_urgent_followup_signal(db, website):
    call = _make_call(website)
    lss.score_call(
        call,
        extraction_data={"follow_ups": [{"description": "send quote", "urgency": "immediate"}]},
    )
    assert call.lead_signals.get("urgent_followup") == 10


def test_buying_keywords_signal(db, website):
    call = _make_call(
        website,
        transcript="hi i'd like to know your pricing and get a quote please",
    )
    lss.score_call(call, extraction_data={})
    assert call.lead_signals.get("buying_keywords") == 15


# ── Threshold + lifecycle tests ────────────────────────────────────────────────


def test_threshold_promotes_to_possible_lead(db, website):
    """email + company + sales intent + positive sentiment + real-conv = 75."""
    call = _make_call(
        website,
        caller_email="x@y.com",
        caller_company="Acme",
        call_intent="sales",
        sentiment="positive",
    )
    lss.score_call(call, extraction_data={})
    assert call.lead_score == 75
    assert call.is_possible_lead is True


def test_score_capped_at_100(db, website):
    """Every signal firing at once should not exceed the cap."""
    call = _make_call(
        website,
        caller_email="x@y.com",
        caller_company="Acme",
        call_intent="sales",
        sentiment="positive",
        transcript="how much for a demo and pricing and a quote",
    )
    lss.score_call(
        call,
        extraction_data={
            "appointments_detected": [{"date": "x", "time": "y"}],
            "follow_ups": [{"description": "x", "urgency": "immediate"}],
        },
    )
    assert call.lead_score == lss.SCORE_CAP


def test_dismissed_call_never_reflagged(db, website):
    from django.utils import timezone

    call = _make_call(
        website,
        caller_email="x@y.com",
        call_intent="sales",
        sentiment="positive",
        caller_company="Acme",
        lead_dismissed_at=timezone.now(),
    )
    lss.score_call(call, extraction_data={})
    assert call.is_possible_lead is False
    # Score is still computed for visibility.
    assert call.lead_score >= lss.DEFAULT_THRESHOLD


def test_already_promoted_call_never_reflagged(db, website, user):
    """A call linked to a Lead row stays linked; we don't surface it again."""
    from apps.analytics.models import Visitor
    from apps.leads.models import Lead

    visitor = Visitor.objects.create(website=website, fingerprint_hash="abc")
    lead = Lead.objects.create(visitor=visitor, website=website)

    call = _make_call(
        website,
        caller_email="x@y.com",
        caller_company="Acme",
        call_intent="sales",
        sentiment="positive",
        lead=lead,
    )
    lss.score_call(call, extraction_data={})
    assert call.is_possible_lead is False


def test_persist_false_does_not_save(db, website):
    call = _make_call(website, caller_email="x@y.com")
    lss.score_call(call, extraction_data={}, persist=False)
    fresh = CallLog.objects.get(pk=call.pk)
    assert fresh.lead_score == 0
    assert fresh.lead_signals == {}


def test_signal_failure_does_not_break_scoring(db, website, monkeypatch):
    """A bug in one signal must not stop the others from running."""

    def boom(call_log, extracted):
        raise RuntimeError("explode")

    monkeypatch.setattr(lss, "_signal_has_email", boom)
    call = _make_call(website, caller_company="Acme")
    lss.score_call(call, extraction_data={})
    # The healthy signals still ran.
    assert "shared_company" in call.lead_signals
    assert "real_conversation" in call.lead_signals
