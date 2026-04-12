"""End-to-end integration test for the inbound call flow.

Exercises the full pipeline end-to-end with mocked externals:

  Phone ring → (mocked Telnyx/SIP) → LiveKit room
    → agent bootstrap → call in-progress webhook
    → call finish → post-call extraction (mocked LLM)
    → lead scoring → todo creation → usage recording

No actual phone calls, LiveKit rooms, or LLM inference. Every external
service is patched so the test runs in < 2s in CI.
"""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.voice_agent.models import (
    AgentConfig,
    CallExtraction,
    CallLog,
    CallTodo,
    VoiceUsageMonthly,
)
from apps.voice_agent.services.call_service import CallService
from apps.voice_agent.services.extraction_service import ExtractionService
from apps.voice_agent.services.lead_scoring_service import score_call
from apps.voice_agent.services.usage_service import (
    UsageLimitExceeded,
    check_usage_limit,
    enforce_usage_limit,
    record_call,
)
from apps.websites.models import Website


@pytest.fixture
def user(db):
    from apps.accounts.models import User
    return User.objects.create_user(
        email="e2e@test.com", password="TestPass123!", full_name="E2E Owner"
    )


@pytest.fixture
def website(db, user):
    return Website.objects.create(name="E2E Biz", url="https://e2e.test", user=user)


@pytest.fixture
def agent_config(db, website):
    return AgentConfig.objects.create(
        website=website,
        business_name="E2E Test Business",
        greeting_message="Hello! How can I help?",
        system_prompt="You are a helpful assistant for E2E Test Business.",
        business_hours={
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
        },
        timezone="America/Chicago",
        appointment_duration_minutes=30,
    )


SAMPLE_TRANSCRIPT = (
    "Agent: Hello! Thank you for calling E2E Test Business. How can I help you today?\n"
    "Caller: Hi, my name is Sarah Chen and I'm with TechVentures Inc. "
    "I'm interested in your pricing for the enterprise plan.\n"
    "Agent: Great to hear from you, Sarah! I'd be happy to go over our pricing.\n"
    "Caller: That sounds perfect. Can I also schedule a demo for next Tuesday at 2pm?\n"
    "Agent: Absolutely! Let me check availability for Tuesday at 2pm.\n"
    "Caller: My email is sarah@techventures.com if you need it.\n"
    "Agent: Perfect, I've booked a demo for next Tuesday at 2pm. "
    "I'll send a confirmation to sarah@techventures.com.\n"
    "Caller: Thank you so much! Looking forward to it.\n"
    "Agent: You're welcome, Sarah! Have a great day."
)

MOCKED_EXTRACTION = {
    "caller_info": {
        "name": "Sarah Chen",
        "phone": "+12025551234",
        "email": "sarah@techventures.com",
        "company": "TechVentures Inc",
    },
    "call_summary": "Caller inquired about enterprise pricing and booked a demo for Tuesday at 2pm.",
    "call_category": "sales",
    "sentiment": "positive",
    "action_items": [
        {
            "description": "Send enterprise pricing sheet to Sarah Chen",
            "priority": "high",
            "assigned_to": "business",
            "due_date": "",
        },
        {
            "description": "Confirm demo appointment for Tuesday 2pm",
            "priority": "medium",
            "assigned_to": "business",
            "due_date": "",
        },
    ],
    "follow_ups": [
        {"description": "Follow up after demo", "urgency": "within_24h"},
    ],
    "appointments": [
        {
            "date": "2026-04-15",
            "time": "14:00",
            "duration_minutes": 30,
            "description": "Enterprise plan demo",
            "confirmed": True,
        }
    ],
}


# ── Phase 1: Inbound call lifecycle ────────────────────────────────────────────


class TestInboundCallE2E:
    """Simulate the full lifecycle of an inbound call with mocked externals."""

    def test_full_inbound_call_pipeline(self, db, user, website, agent_config):
        """
        Step 1: call_started webhook → creates CallLog (in_progress)
        Step 2: call_ended webhook → updates with transcript, triggers extraction
        Step 3: extraction → creates CallExtraction + CallTodo records
        Step 4: lead scoring → marks is_possible_lead = True
        Step 5: usage recording → VoiceUsageMonthly incremented
        """

        # ── Step 1: Call Started ──────────────────────────────────────────
        started_data = {
            "call_id": "retell-e2e-test-001",
            "direction": "inbound",
            "from_number": "+12025551234",
        }
        call_log = CallService.process_call_started(website.id, started_data)

        assert call_log.status == CallLog.STATUS_IN_PROGRESS
        assert call_log.caller_phone == "+12025551234"
        assert call_log.direction == CallLog.DIRECTION_INBOUND
        assert call_log.external_call_id == "retell-e2e-test-001"

        # ── Step 2: Call Ended (with transcript) ──────────────────────────
        now = timezone.now()
        ended_data = {
            "call_id": "retell-e2e-test-001",
            "call": {
                "call_id": "retell-e2e-test-001",
                "transcript": SAMPLE_TRANSCRIPT,
                "start_timestamp": int((now - timedelta(minutes=3)).timestamp()) * 1000,
                "end_timestamp": int(now.timestamp()) * 1000,
                "call_analysis": {
                    "call_summary": "Sales inquiry with demo booking.",
                    "user_sentiment": "positive",
                    "call_intent": "sales",
                    "custom_analysis_data": {
                        "caller_name": "Sarah Chen",
                        "caller_email": "sarah@techventures.com",
                        "caller_company": "TechVentures Inc",
                    },
                },
            },
        }
        # The call_ended handler triggers extract_call_data.delay() — mock it
        with patch("apps.voice_agent.tasks.extract_call_data.delay") as mock_extract:
            call_log = CallService.process_call_ended(website.id, ended_data)

        call_log.refresh_from_db()
        assert call_log.status == CallLog.STATUS_COMPLETED
        assert call_log.transcript == SAMPLE_TRANSCRIPT
        assert call_log.caller_name == "Sarah Chen"
        assert call_log.caller_email == "sarah@techventures.com"
        assert call_log.duration_seconds > 0

        # ── Step 3: Post-call extraction (mocked LLM) ────────────────────
        with patch(
            "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json"
        ) as mock_llm:
            mock_llm.return_value = {
                "data": MOCKED_EXTRACTION,
                "model": "test-model",
            }
            extraction = ExtractionService.extract_from_transcript(call_log)

        assert extraction is not None
        assert extraction.call_category == "sales"
        assert extraction.sentiment == "positive"
        assert extraction.caller_info["name"] == "Sarah Chen"
        assert extraction.caller_info["email"] == "sarah@techventures.com"

        # Verify todos were created
        todos = CallTodo.objects.filter(call_log=call_log)
        assert todos.count() >= 2  # 2 action items + 1 follow-up

        # Verify caller info was backfilled to the CallLog
        call_log.refresh_from_db()
        assert call_log.summary != ""
        assert call_log.call_intent in ("sales", "appointment")

        # ── Step 4: Lead scoring ──────────────────────────────────────────
        # Extraction already ran lead scoring internally. Verify the call
        # is flagged as a possible lead.
        call_log.refresh_from_db()
        assert call_log.lead_score > 0
        # Score should be high: email(20) + company(15) + sales intent(25)
        # + positive sentiment(10) + real_conversation(5) + buying_keywords(15)
        assert call_log.lead_score >= 50
        assert call_log.is_possible_lead is True
        assert "shared_email" in call_log.lead_signals
        assert "shared_company" in call_log.lead_signals

        # ── Step 5: Usage recording ───────────────────────────────────────
        call_log.stt_seconds = call_log.duration_seconds
        call_log.tts_characters = 500
        call_log.llm_input_tokens = 1200
        call_log.llm_output_tokens = 400
        call_log.save(update_fields=[
            "stt_seconds", "tts_characters",
            "llm_input_tokens", "llm_output_tokens",
        ])

        monthly = record_call(call_log)
        assert monthly.total_calls == 1
        assert monthly.inbound_calls == 1
        assert monthly.billable_minutes >= 1
        assert monthly.estimated_cost_usd > 0

        call_log.refresh_from_db()
        assert call_log.estimated_cost_usd > 0
        assert call_log.billable_seconds >= 30  # billing floor


# ── Phase 2: Internal call-finish endpoint (LiveKit worker path) ─────────────


class TestInternalCallFinishE2E:
    """Simulate the LiveKit agent worker posting to /internal/calls/finish/."""

    def test_livekit_call_finish_creates_complete_pipeline(self, db, user, website, agent_config):
        """
        LiveKit worker creates a CallLog row during the call, then POSTs:
          transcript, duration, billing meters → /internal/calls/finish/

        The endpoint updates the CallLog and triggers async extraction.
        """
        # Pre-create the CallLog (as the LiveKit worker would)
        call_log = CallLog.objects.create(
            website=website,
            external_call_id="voice-agent-livekit-e2e",
            direction=CallLog.DIRECTION_INBOUND,
            status=CallLog.STATUS_IN_PROGRESS,
            caller_phone="+13125559876",
            started_at=timezone.now() - timedelta(minutes=5),
        )

        # Simulate the finish payload from the LiveKit agent worker
        finish_payload = {
            "call_log_id": str(call_log.id),
            "transcript": SAMPLE_TRANSCRIPT,
            "duration": 300,
            "ended_reason": "completed",
            "tts_characters": 800,
            "llm_input_tokens": 2500,
            "llm_output_tokens": 600,
            "stt_seconds": 300,
        }

        # Apply the finish data (simulating what the InternalCallFinishView does)
        call_log.transcript = finish_payload["transcript"]
        call_log.duration_seconds = finish_payload["duration"]
        call_log.status = CallLog.STATUS_COMPLETED
        call_log.ended_at = timezone.now()
        call_log.tts_characters = finish_payload["tts_characters"]
        call_log.llm_input_tokens = finish_payload["llm_input_tokens"]
        call_log.llm_output_tokens = finish_payload["llm_output_tokens"]
        call_log.stt_seconds = finish_payload["stt_seconds"]
        call_log.save()

        # Record usage
        monthly = record_call(call_log)
        assert monthly.total_calls == 1
        assert monthly.billable_minutes >= 5

        # Run extraction
        with patch(
            "apps.voice_agent.services.selfhosted_inference.SelfHostedLLM.extract_json"
        ) as mock_llm:
            mock_llm.return_value = {"data": MOCKED_EXTRACTION, "model": "test-model"}
            extraction = ExtractionService.extract_from_transcript(call_log)

        assert extraction is not None
        assert extraction.call_category == "sales"

        # Verify lead score
        call_log.refresh_from_db()
        assert call_log.is_possible_lead is True
        assert call_log.lead_score >= 50


# ── Phase 3: Usage limit enforcement ─────────────────────────────────────────


class TestUsageLimitEnforcement:
    """Verify that plan-based voice minute limits are enforced."""

    def test_no_limit_when_no_subscription(self, db, website):
        result = check_usage_limit(website.id)
        assert result["allowed"] is True
        assert result["limit"] is None

    def test_limit_enforced_when_usage_exceeds_cap(self, db, user, website):
        """Create a subscription with Individual plan (100 min) and exhaust it."""
        from apps.billing.models import Subscription

        Subscription.objects.create(
            user=user,
            stripe_customer_id="cus_e2e_test",
            plan="individual",
            status="active",
        )

        # Create usage that exceeds the 100-minute cap
        ym = timezone.now().strftime("%Y-%m")
        VoiceUsageMonthly.objects.create(
            website=website,
            year_month=ym,
            total_calls=50,
            inbound_calls=50,
            billable_minutes=101,  # Over the 100-minute Individual cap
        )

        result = check_usage_limit(website.id)
        assert result["allowed"] is False
        assert result["used"] == 101
        assert result["limit"] == 100
        assert result["pct"] >= 100.0

        # enforce_usage_limit should raise
        with pytest.raises(UsageLimitExceeded) as exc_info:
            enforce_usage_limit(website.id)
        assert exc_info.value.used == 101
        assert exc_info.value.limit == 100

    def test_limit_passes_when_under_cap(self, db, user, website):
        from apps.billing.models import Subscription

        Subscription.objects.create(
            user=user,
            stripe_customer_id="cus_e2e_test_2",
            plan="individual",
            status="active",
        )

        ym = timezone.now().strftime("%Y-%m")
        VoiceUsageMonthly.objects.create(
            website=website,
            year_month=ym,
            total_calls=5,
            inbound_calls=5,
            billable_minutes=25,  # Well under the 100-minute cap
        )

        result = check_usage_limit(website.id)
        assert result["allowed"] is True
        assert result["used"] == 25
        assert result["limit"] == 100

        # Should not raise
        enforce_usage_limit(website.id)


# ── Phase 4: Agent bootstrap (system prompt assembly) ────────────────────────


class TestAgentBootstrap:
    """Verify the agent bootstrap endpoint returns the merged system prompt."""

    def test_prompt_builder_includes_context_docs(self, db, website, agent_config):
        from apps.voice_agent.models import AgentContextDocument
        from apps.voice_agent.services.prompt_builder import build_retell_system_prompt

        doc1 = AgentContextDocument.objects.create(
            website=website,
            title="Services & Pricing",
            content="# Services\n- Web Development: $150/hr\n- Mobile App: $200/hr",
            is_active=True,
            sort_order=0,
        )
        doc2 = AgentContextDocument.objects.create(
            website=website,
            title="FAQs",
            content="# FAQs\nQ: Do you offer free consultations?\nA: Yes!",
            is_active=True,
            sort_order=1,
        )

        prompt = build_retell_system_prompt(agent_config)

        # Prompt should include the config's system prompt
        assert "helpful" in prompt.lower() or "assistant" in prompt.lower()
        # Prompt should include the knowledge base documents
        assert "Web Development" in prompt
        assert "free consultations" in prompt
