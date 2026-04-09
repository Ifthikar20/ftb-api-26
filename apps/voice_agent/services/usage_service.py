"""Voice agent usage tracking & cost estimation.

Every completed call ticks four meters: STT seconds, TTS characters, LLM
input/output tokens, and billable talk seconds (with a 30s minimum-bill
floor that matches industry convention). Per-call totals live on
:class:`CallLog`; per-month rollups live on :class:`VoiceUsageMonthly` so
the dashboard can render in O(1) without scanning the call log.

Per-meter unit prices come from settings so they can be tuned without
a code change. The defaults match the cost grid that used to be on the
old "Cost Comparison" card (Telnyx + Deepgram + GPT-4o-mini + Cartesia
self-hosted): ~$0.017 per minute of conversation. If you change pricing
contracts, edit `settings.VOICE_PRICE_*` — never inline magic numbers
into views or models.

The aggregation update uses ``F()`` increments inside an
``update_or_create`` so two simultaneous call-finish webhooks cannot
clobber each other.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.voice_agent.models import CallLog, VoiceUsageMonthly

logger = logging.getLogger("apps")

# ── Default unit prices (USD) ─────────────────────────────────────────────────
# Override any of these in settings to match your actual vendor contract.
DEFAULT_PRICES = {
    "VOICE_PRICE_STT_PER_SEC": Decimal("0.0000667"),     # Deepgram nova-3 ~$0.004/min
    "VOICE_PRICE_TTS_PER_CHAR": Decimal("0.000015"),     # ~$15 per 1M chars
    "VOICE_PRICE_LLM_INPUT_PER_TOKEN": Decimal("0.00000015"),   # gpt-4o-mini in
    "VOICE_PRICE_LLM_OUTPUT_PER_TOKEN": Decimal("0.0000006"),   # gpt-4o-mini out
    "VOICE_PRICE_TELNYX_PER_MIN": Decimal("0.005"),      # PSTN egress
    "VOICE_BILLABLE_FLOOR_SECONDS": 30,                  # min billable per call
}


def _price(key: str) -> Decimal:
    """Return a configured price as a Decimal, falling back to the default."""
    raw = getattr(settings, key, None)
    if raw is None:
        return DEFAULT_PRICES[key]
    return Decimal(str(raw))


@dataclass
class CallCost:
    """Breakdown of a single call's cost. Helpful for audit / debugging."""

    billable_seconds: int
    stt_usd: Decimal
    tts_usd: Decimal
    llm_in_usd: Decimal
    llm_out_usd: Decimal
    telnyx_usd: Decimal
    total_usd: Decimal


def estimate_call_cost(call_log: CallLog) -> CallCost:
    """Compute (but don't persist) the cost breakdown for a CallLog row."""
    floor = int(_price("VOICE_BILLABLE_FLOOR_SECONDS"))
    billable = max(call_log.duration_seconds or 0, floor if call_log.duration_seconds else 0)
    minutes_ceil = math.ceil(billable / 60) if billable else 0

    stt = Decimal(call_log.stt_seconds or call_log.duration_seconds or 0) * _price("VOICE_PRICE_STT_PER_SEC")
    tts = Decimal(call_log.tts_characters or 0) * _price("VOICE_PRICE_TTS_PER_CHAR")
    llm_in = Decimal(call_log.llm_input_tokens or 0) * _price("VOICE_PRICE_LLM_INPUT_PER_TOKEN")
    llm_out = Decimal(call_log.llm_output_tokens or 0) * _price("VOICE_PRICE_LLM_OUTPUT_PER_TOKEN")
    telnyx = Decimal(minutes_ceil) * _price("VOICE_PRICE_TELNYX_PER_MIN")
    total = (stt + tts + llm_in + llm_out + telnyx).quantize(Decimal("0.0001"))

    return CallCost(
        billable_seconds=billable,
        stt_usd=stt.quantize(Decimal("0.0001")),
        tts_usd=tts.quantize(Decimal("0.0001")),
        llm_in_usd=llm_in.quantize(Decimal("0.0001")),
        llm_out_usd=llm_out.quantize(Decimal("0.0001")),
        telnyx_usd=telnyx.quantize(Decimal("0.0001")),
        total_usd=total,
    )


def _year_month(dt) -> str:
    return dt.strftime("%Y-%m")


@transaction.atomic
def record_call(call_log: CallLog) -> VoiceUsageMonthly:
    """Persist per-call cost on the CallLog and roll into VoiceUsageMonthly.

    Idempotent across re-runs of the same call: the per-call cost overwrites
    in place, but the monthly delta only fires when the call's
    ``billable_seconds`` is being set for the first time. Re-running on a
    call that already has ``billable_seconds`` is a no-op for the rollup —
    use the management command for full rebuilds instead.
    """
    is_first_record = (call_log.billable_seconds or 0) == 0

    cost = estimate_call_cost(call_log)
    call_log.billable_seconds = cost.billable_seconds
    if not call_log.stt_seconds:
        call_log.stt_seconds = call_log.duration_seconds or 0
    call_log.estimated_cost_usd = cost.total_usd
    call_log.save(update_fields=[
        "billable_seconds", "stt_seconds", "estimated_cost_usd", "updated_at",
    ])

    if not is_first_record:
        # Already counted in the rollup. Skip the increment to avoid
        # double-counting on retries; the nightly reconciler is the only
        # path that should ever rebuild from CallLog.
        return _get_or_create_month(call_log)

    return _increment_monthly(call_log, cost)


def _get_or_create_month(call_log: CallLog) -> VoiceUsageMonthly:
    ym = _year_month(call_log.created_at or timezone.now())
    obj, _ = VoiceUsageMonthly.objects.get_or_create(
        website_id=call_log.website_id, year_month=ym
    )
    return obj


def _increment_monthly(call_log: CallLog, cost: CallCost) -> VoiceUsageMonthly:
    ym = _year_month(call_log.created_at or timezone.now())
    minutes = math.ceil(cost.billable_seconds / 60) if cost.billable_seconds else 0
    is_inbound = call_log.direction == CallLog.DIRECTION_INBOUND

    # update_or_create gives us a single round-trip if the row exists. We
    # then immediately apply F() increments so two concurrent webhooks
    # don't race a read-modify-write cycle.
    VoiceUsageMonthly.objects.update_or_create(
        website_id=call_log.website_id,
        year_month=ym,
        defaults={},
    )
    VoiceUsageMonthly.objects.filter(
        website_id=call_log.website_id, year_month=ym
    ).update(
        total_calls=F("total_calls") + 1,
        inbound_calls=F("inbound_calls") + (1 if is_inbound else 0),
        outbound_calls=F("outbound_calls") + (0 if is_inbound else 1),
        total_seconds=F("total_seconds") + (call_log.duration_seconds or 0),
        billable_minutes=F("billable_minutes") + minutes,
        llm_input_tokens=F("llm_input_tokens") + (call_log.llm_input_tokens or 0),
        llm_output_tokens=F("llm_output_tokens") + (call_log.llm_output_tokens or 0),
        tts_characters=F("tts_characters") + (call_log.tts_characters or 0),
        estimated_cost_usd=F("estimated_cost_usd") + cost.total_usd,
    )
    obj = VoiceUsageMonthly.objects.get(
        website_id=call_log.website_id, year_month=ym
    )
    logger.info(
        "voice_usage_recorded",
        extra={
            "call_id": str(call_log.id),
            "website_id": str(call_log.website_id),
            "year_month": ym,
            "minutes": minutes,
            "cost_usd": str(cost.total_usd),
        },
    )
    return obj


def get_current_period(website_id, *, plan_limit_minutes: Optional[int] = None) -> dict:
    """Return the dashboard payload for ``website_id``'s current month."""
    ym = _year_month(timezone.now())
    obj = VoiceUsageMonthly.objects.filter(
        website_id=website_id, year_month=ym
    ).first()
    if obj is None:
        return {
            "year_month": ym,
            "total_calls": 0,
            "inbound_calls": 0,
            "outbound_calls": 0,
            "billable_minutes": 0,
            "estimated_cost_usd": "0.0000",
            "plan_limit_minutes": plan_limit_minutes,
            "plan_limit_pct": 0.0,
        }
    pct = 0.0
    if plan_limit_minutes:
        pct = round(min(100.0, (obj.billable_minutes / plan_limit_minutes) * 100), 1)
    return {
        "year_month": obj.year_month,
        "total_calls": obj.total_calls,
        "inbound_calls": obj.inbound_calls,
        "outbound_calls": obj.outbound_calls,
        "billable_minutes": obj.billable_minutes,
        "total_seconds": obj.total_seconds,
        "llm_input_tokens": obj.llm_input_tokens,
        "llm_output_tokens": obj.llm_output_tokens,
        "tts_characters": obj.tts_characters,
        "estimated_cost_usd": str(obj.estimated_cost_usd),
        "plan_limit_minutes": plan_limit_minutes,
        "plan_limit_pct": pct,
    }


def get_history(website_id, *, months: int = 6) -> list[dict]:
    """Return the trailing-N-month history for sparkline / chart rendering."""
    qs = VoiceUsageMonthly.objects.filter(website_id=website_id).order_by("-year_month")[:months]
    return [
        {
            "year_month": row.year_month,
            "total_calls": row.total_calls,
            "billable_minutes": row.billable_minutes,
            "estimated_cost_usd": str(row.estimated_cost_usd),
        }
        for row in reversed(list(qs))
    ]


def rebuild_month(website_id, year_month: str) -> VoiceUsageMonthly:
    """Recompute a single month's totals from CallLog. Used by the
    nightly reconciler and the management command. Safe to run repeatedly.
    """
    from django.db.models import Count, Sum

    rows = (
        CallLog.objects
        .filter(
            website_id=website_id,
            created_at__year=int(year_month.split("-")[0]),
            created_at__month=int(year_month.split("-")[1]),
        )
        .aggregate(
            total_calls=Count("id"),
            inbound_calls=Count("id", filter=models_q_inbound()),
            outbound_calls=Count("id", filter=models_q_outbound()),
            total_seconds=Sum("duration_seconds"),
            billable_seconds_sum=Sum("billable_seconds"),
            llm_in=Sum("llm_input_tokens"),
            llm_out=Sum("llm_output_tokens"),
            tts=Sum("tts_characters"),
            cost=Sum("estimated_cost_usd"),
        )
    )
    obj, _ = VoiceUsageMonthly.objects.update_or_create(
        website_id=website_id,
        year_month=year_month,
        defaults={
            "total_calls": rows["total_calls"] or 0,
            "inbound_calls": rows["inbound_calls"] or 0,
            "outbound_calls": rows["outbound_calls"] or 0,
            "total_seconds": rows["total_seconds"] or 0,
            "billable_minutes": math.ceil((rows["billable_seconds_sum"] or 0) / 60),
            "llm_input_tokens": rows["llm_in"] or 0,
            "llm_output_tokens": rows["llm_out"] or 0,
            "tts_characters": rows["tts"] or 0,
            "estimated_cost_usd": rows["cost"] or Decimal("0"),
        },
    )
    return obj


def models_q_inbound():
    from django.db.models import Q
    return Q(direction=CallLog.DIRECTION_INBOUND)


def models_q_outbound():
    from django.db.models import Q
    return Q(direction=CallLog.DIRECTION_OUTBOUND)
