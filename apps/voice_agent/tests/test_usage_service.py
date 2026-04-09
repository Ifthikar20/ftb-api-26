"""Tests for voice agent usage tracking & cost estimation.

These tests don't touch the LiveKit worker — we exercise the service
boundary the worker calls (``record_call``) plus the read helpers the
dashboard hits. Pricing is asserted against the documented defaults so
a tweak to ``DEFAULT_PRICES`` will fail loudly here, which is the goal:
nobody should silently change billing rates.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.voice_agent.models import CallLog, VoiceUsageMonthly
from apps.voice_agent.services import usage_service as us
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


def _call(website, **overrides):
    defaults = dict(
        website=website,
        caller_phone="+12025550123",
        status=CallLog.STATUS_COMPLETED,
        direction=CallLog.DIRECTION_INBOUND,
        duration_seconds=120,
    )
    defaults.update(overrides)
    return CallLog.objects.create(**defaults)


# ── estimate_call_cost ────────────────────────────────────────────────────────


def test_estimate_zero_duration_returns_zero(db, website):
    cost = us.estimate_call_cost(_call(website, duration_seconds=0))
    assert cost.total_usd == Decimal("0.0000")
    assert cost.billable_seconds == 0


def test_estimate_applies_30s_floor(db, website):
    """A 5-second call still bills as 30 seconds, matching vendor convention."""
    cost = us.estimate_call_cost(_call(website, duration_seconds=5))
    assert cost.billable_seconds == 30


def test_estimate_telnyx_rounds_minutes_up(db, website):
    """61 seconds = 2 billable minutes for the PSTN leg."""
    call = _call(website, duration_seconds=61)
    cost = us.estimate_call_cost(call)
    # 2 min * $0.005 = $0.0100
    assert cost.telnyx_usd == Decimal("0.0100")


def test_estimate_combines_meters(db, website):
    """All four meters contribute to the total."""
    call = _call(
        website,
        duration_seconds=120,
        tts_characters=500,
        llm_input_tokens=1_000,
        llm_output_tokens=400,
    )
    cost = us.estimate_call_cost(call)
    # stt:    120 * 0.0000667    = 0.008004
    # tts:    500 * 0.000015     = 0.007500
    # llm_in: 1000 * 0.00000015  = 0.000150
    # llm_out: 400 * 0.0000006   = 0.000240
    # telnyx: ceil(120/60)*0.005 = 0.010000
    # total = 0.025894 -> quantized 0.0259
    assert cost.total_usd == Decimal("0.0259")


# ── record_call (per-call + monthly rollup) ───────────────────────────────────


def test_record_call_persists_per_call_cost(db, website):
    call = _call(website, duration_seconds=60)
    us.record_call(call)
    call.refresh_from_db()
    assert call.billable_seconds == 60
    assert call.estimated_cost_usd > 0


def test_record_call_creates_monthly_row(db, website):
    call = _call(website, duration_seconds=120, llm_input_tokens=500)
    us.record_call(call)
    row = VoiceUsageMonthly.objects.get(website=website)
    assert row.total_calls == 1
    assert row.inbound_calls == 1
    assert row.outbound_calls == 0
    assert row.billable_minutes == 2
    assert row.llm_input_tokens == 500


def test_record_call_aggregates_multiple(db, website):
    us.record_call(_call(website, duration_seconds=60))
    us.record_call(_call(website, duration_seconds=180, direction=CallLog.DIRECTION_OUTBOUND))
    row = VoiceUsageMonthly.objects.get(website=website)
    assert row.total_calls == 2
    assert row.inbound_calls == 1
    assert row.outbound_calls == 1
    assert row.billable_minutes == 4  # 1 + 3


def test_record_call_is_idempotent(db, website):
    """Re-running on a call that's already been counted must not double-bill."""
    call = _call(website, duration_seconds=120)
    us.record_call(call)
    us.record_call(call)
    us.record_call(call)
    row = VoiceUsageMonthly.objects.get(website=website)
    assert row.total_calls == 1


# ── get_current_period / get_history ──────────────────────────────────────────


def test_get_current_period_zero_when_no_calls(db, website):
    payload = us.get_current_period(website.id, plan_limit_minutes=1000)
    assert payload["billable_minutes"] == 0
    assert payload["plan_limit_pct"] == 0.0


def test_get_current_period_includes_pct_when_limit(db, website):
    us.record_call(_call(website, duration_seconds=600))  # 10 minutes
    payload = us.get_current_period(website.id, plan_limit_minutes=100)
    assert payload["billable_minutes"] == 10
    assert payload["plan_limit_pct"] == 10.0


def test_get_current_period_omits_pct_when_no_limit(db, website):
    us.record_call(_call(website, duration_seconds=120))
    payload = us.get_current_period(website.id, plan_limit_minutes=None)
    assert payload["plan_limit_minutes"] is None
    assert payload["plan_limit_pct"] == 0.0


def test_get_history_returns_reverse_chrono_then_chrono(db, website):
    """History should be oldest -> newest so a chart can render left-to-right."""
    VoiceUsageMonthly.objects.create(website=website, year_month="2026-02", billable_minutes=10)
    VoiceUsageMonthly.objects.create(website=website, year_month="2026-03", billable_minutes=20)
    VoiceUsageMonthly.objects.create(website=website, year_month="2026-04", billable_minutes=30)
    history = us.get_history(website.id, months=6)
    assert [h["year_month"] for h in history] == ["2026-02", "2026-03", "2026-04"]
