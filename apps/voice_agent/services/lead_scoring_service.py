"""Transcript-based lead detection.

After every completed call we want to decide: was the caller a possible
lead? The full LLM extraction has already populated structured fields on
:class:`CallLog` and :class:`CallExtraction` (caller name, email, company,
intent, sentiment, follow-ups, action items, transcript). This service
turns that into a single ``lead_score`` and an ``is_possible_lead`` flag,
without making any new model API calls.

The scoring is intentionally a transparent rule engine — every signal that
fires is recorded in ``CallLog.lead_signals`` so the UI can explain *why*
a call was flagged. That matters because we never auto-push to the Lead
table; the user reviews the queue and promotes manually.

Adding a new signal: append a new ``_signal_*`` function and register it
in ``SIGNALS``. Each function returns ``(label, points)`` or ``None``.
Total score is capped at 100. The threshold defaults to 50 and can be
overridden per request, e.g. for tuning experiments.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Iterable, Optional, Tuple

logger = logging.getLogger("apps")

DEFAULT_THRESHOLD = 50
SCORE_CAP = 100

# Words that strongly suggest a buying / sales intent.
_BUYING_KEYWORDS = re.compile(
    r"\b(price|pricing|cost|quote|estimate|buy|purchase|interested in|"
    r"sign up|demo|trial|onboard|get started|how much|when can i)\b",
    re.IGNORECASE,
)

_HOT_INTENTS = {"sales", "appointment", "inquiry"}
_HOT_SENTIMENTS = {"positive"}


Signal = Tuple[str, int]
SignalFn = Callable[[object, dict], Optional[Signal]]


def _signal_has_email(call_log, extracted: dict) -> Optional[Signal]:
    if call_log.caller_email or extracted.get("caller_info", {}).get("email"):
        return ("shared_email", 20)
    return None


def _signal_has_company(call_log, extracted: dict) -> Optional[Signal]:
    if call_log.caller_company or extracted.get("caller_info", {}).get("company"):
        return ("shared_company", 15)
    return None


def _signal_intent(call_log, extracted: dict) -> Optional[Signal]:
    intent = (call_log.call_intent or extracted.get("call_category") or "").lower()
    if intent in _HOT_INTENTS:
        return (f"intent_{intent}", 25)
    return None


def _signal_sentiment(call_log, extracted: dict) -> Optional[Signal]:
    sentiment = (call_log.sentiment or extracted.get("sentiment") or "").lower()
    if sentiment in _HOT_SENTIMENTS:
        return ("positive_sentiment", 10)
    return None


def _signal_appointment_discussed(call_log, extracted: dict) -> Optional[Signal]:
    appts = extracted.get("appointments_detected") or extracted.get("appointments") or []
    if appts:
        return ("appointment_discussed", 20)
    return None


def _signal_immediate_followup(call_log, extracted: dict) -> Optional[Signal]:
    follow_ups = extracted.get("follow_ups") or []
    for fu in follow_ups:
        if (fu.get("urgency") or "").lower() in ("immediate", "within_24h"):
            return ("urgent_followup", 10)
    return None


def _signal_buying_keywords(call_log, extracted: dict) -> Optional[Signal]:
    transcript = call_log.transcript or ""
    if _BUYING_KEYWORDS.search(transcript):
        return ("buying_keywords", 15)
    return None


def _signal_call_completed(call_log, extracted: dict) -> Optional[Signal]:
    # A 0-second hangup or a missed call is never a lead. We require
    # something resembling a real conversation before any other signal
    # can push the score over the threshold.
    if (call_log.duration_seconds or 0) < 20:
        return None
    return ("real_conversation", 5)


SIGNALS: Iterable[SignalFn] = (
    _signal_call_completed,
    _signal_has_email,
    _signal_has_company,
    _signal_intent,
    _signal_sentiment,
    _signal_appointment_discussed,
    _signal_immediate_followup,
    _signal_buying_keywords,
)


def score_call(
    call_log,
    *,
    extraction_data: dict | None = None,
    threshold: int = DEFAULT_THRESHOLD,
    persist: bool = True,
):
    """Score a call's lead potential.

    ``extraction_data`` should be the dict returned by the LLM extractor; if
    omitted, the function falls back to the ``CallExtraction`` row attached
    to the call. Returns the updated ``CallLog`` (saved iff ``persist``).

    The function is idempotent and safe to call multiple times — the
    signals dict is recomputed from current state every run.
    """
    if extraction_data is None:
        extraction_data = _load_extraction(call_log)

    signals: dict[str, int] = {}
    for fn in SIGNALS:
        try:
            result = fn(call_log, extraction_data)
        except Exception:  # noqa: BLE001 — one bad signal shouldn't kill scoring
            logger.exception(
                "lead_signal_failed",
                extra={"call_id": str(call_log.id), "signal": fn.__name__},
            )
            continue
        if result is None:
            continue
        label, points = result
        signals[label] = points

    score = min(SCORE_CAP, sum(signals.values()))
    is_possible = (
        score >= threshold
        and "real_conversation" in signals
        # Don't re-flag a call the user already triaged.
        and call_log.lead_dismissed_at is None
        and call_log.lead_id is None
    )

    call_log.lead_score = score
    call_log.lead_signals = signals
    call_log.is_possible_lead = is_possible

    if persist:
        call_log.save(
            update_fields=[
                "lead_score", "lead_signals", "is_possible_lead", "updated_at",
            ]
        )

    logger.info(
        "lead_scored",
        extra={
            "call_id": str(call_log.id),
            "score": score,
            "is_possible_lead": is_possible,
            "signals": list(signals.keys()),
        },
    )
    return call_log


def _load_extraction(call_log) -> dict:
    """Pull the most recent CallExtraction for this call into a flat dict."""
    from apps.voice_agent.models import CallExtraction

    try:
        ext = CallExtraction.objects.get(call_log=call_log)
    except CallExtraction.DoesNotExist:
        return {}
    return {
        "caller_info": ext.caller_info or {},
        "call_summary": ext.call_summary,
        "call_category": ext.call_category,
        "sentiment": ext.sentiment,
        "follow_ups": ext.follow_ups or [],
        "appointments_detected": ext.appointments_detected or [],
    }
