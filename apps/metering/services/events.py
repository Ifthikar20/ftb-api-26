"""
Build Polar `llm_usage` events from AITokenUsage ledger rows and stage
them in the transactional outbox.

The outbox row is created inside the caller's transaction (see
core.ai_tracking.record_usage), so a ledger row and its event commit or
roll back together. Delivery happens after commit: either the debounced
Celery task (POLAR_INGEST_MODE=celery) or an inline flush
(POLAR_INGEST_MODE=inline, for dev machines with no workers).
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("metering.events")

# Debounce key: at most one flush dispatch per window regardless of how
# many usage rows commit in a burst (audit fan-out writes hundreds).
_FLUSH_DEBOUNCE_KEY = "polar_flush_scheduled"
_FLUSH_DEBOUNCE_SECONDS = 10


def ingest_mode() -> str:
    mode = getattr(settings, "POLAR_INGEST_MODE", "off")
    return mode if mode in ("celery", "inline", "off") else "off"


def build_event(usage) -> dict:
    """Map one AITokenUsage row onto the canonical Polar event dict.

    Metadata values must be str/int/float/bool (Polar caps: 50 pairs,
    strings 500 chars); None-valued keys are omitted.
    """
    meta_src = usage.metadata or {}
    metadata = {
        "idempotency_key": usage.idempotency_key,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "model": usage.model_name,
        "provider": usage.provider,
        "module": usage.module,
        "role": str(meta_src.get("role") or "upstream"),
        "actor": str(meta_src.get("actor") or "user"),
        "duration_ms": usage.duration_ms,
        # Integer micro-USD: exact against the ledger's 6-decimal USD
        # column, and the unit Phase 2 credits will be denominated in.
        "cost_micros": int(round(float(usage.estimated_cost_usd) * 1_000_000)),
    }
    if usage.website_id:
        metadata["website_id"] = str(usage.website_id)
    audit_id = meta_src.get("audit_id")
    if audit_id:
        metadata["audit_id"] = str(audit_id)[:500]

    return {
        "name": settings.POLAR_EVENT_NAME,
        "external_customer_id": str(usage.user_id),
        # Polar deduplicates on external_id — the exactly-once anchor.
        "external_id": usage.idempotency_key,
        "metadata": metadata,
    }


def enqueue_usage_event(usage) -> None:
    """Stage one ledger row for delivery. No-op when metering is off or
    the row is unattributed (pre-signup onboarding scans stay local)."""
    if ingest_mode() == "off":
        return
    if usage.user_id is None or not usage.idempotency_key:
        return

    from apps.metering.models import PolarEventOutbox

    event = build_event(usage)
    PolarEventOutbox.objects.get_or_create(
        idempotency_key=usage.idempotency_key,
        defaults={
            "usage": usage,
            "external_customer_id": event["external_customer_id"],
            "name": event["name"],
            "payload": event,
        },
    )


def schedule_flush() -> None:
    """Post-commit hook: kick delivery according to the ingest mode."""
    mode = ingest_mode()
    if mode == "celery":
        try:
            if cache.add(_FLUSH_DEBOUNCE_KEY, 1, _FLUSH_DEBOUNCE_SECONDS):
                from apps.metering.tasks import flush_polar_events

                flush_polar_events.delay()
        except Exception:
            # The 2-minute beat sweeper is the safety net for lost kicks.
            logger.warning("polar flush dispatch failed", exc_info=True)
    elif mode == "inline":
        try:
            from apps.metering.tasks import flush_outbox_once

            flush_outbox_once()
        except Exception:
            logger.warning("inline polar flush failed", exc_info=True)
