"""
Hot-path spend accounting for cap notifications.

record_usage() used to run TWO aggregate queries against the full ledger
on every single LLM call just to decide whether to notify at 80%/100% of
the allowance. This module replaces that with a Redis integer counter
(micro-USD) per user per billing period:

  - lazily seeded from ONE ledger aggregate the first time a period is
    touched, then incremented in O(1) per call;
  - threshold crossings enqueue apps.metering.tasks.notify_cap_threshold,
    which re-verifies against the ledger (authoritative) before creating
    the notification, so counter drift can produce at worst a no-op task;
  - any cache outage skips silently — notifications are best-effort and
    the hard spend wall (core.llm.base.allowance_denial) does its own
    ledger check regardless.
"""
from __future__ import annotations

import logging

from django.core.cache import cache

logger = logging.getLogger("metering.spend")

_CAP_CACHE_SECONDS = 600


def _counter_key(user_id, period_key: str) -> str:
    return f"ai_spend_micros:{user_id}:{period_key}"


def effective_cap_cached(user) -> float:
    """effective_ai_cap(user), cached briefly — it hits Subscription/plan."""
    from core.ai_tracking import effective_ai_cap

    key = f"ai_cap_usd:{user.id}"
    try:
        cached = cache.get(key)
        if cached is not None:
            return float(cached)
    except Exception:
        return effective_ai_cap(user)
    cap = effective_ai_cap(user)
    try:
        cache.set(key, cap, _CAP_CACHE_SECONDS)
    except Exception:
        pass
    return cap


def bump(user, cost_usd: float) -> None:
    """Add one call's cost to the period counter; fire threshold tasks on
    crossings. Never raises."""
    try:
        from apps.metering.services.periods import billing_period_for
        from core.ai_tracking import AI_SPEND_WARN_RATIO

        cap = effective_cap_cached(user)
        if cap <= 0:
            return

        period = billing_period_for(user)
        key = _counter_key(user.id, period.key)
        delta = int(round(cost_usd * 1_000_000))
        ttl = int((period.end - period.start).total_seconds()) + 3 * 86400

        try:
            post = cache.incr(key, delta)
        except ValueError:
            # First touch this period: seed from the ledger, then account
            # for races (another process may have seeded meanwhile).
            seeded = _ledger_period_micros(user, period)
            if not cache.add(key, seeded + delta, ttl):
                post = cache.incr(key, delta)
            else:
                post = seeded + delta

        pre = post - delta
        cap_micros = int(cap * 1_000_000)
        warn_micros = int(cap_micros * AI_SPEND_WARN_RATIO)
        for ntype, threshold in (
            ("ai_cap_exceeded", cap_micros),
            ("ai_cap_warning", warn_micros),
        ):
            if pre < threshold <= post:
                _dispatch_notify(user.id, ntype)
                break
    except Exception:
        logger.debug("spend counter bump failed", exc_info=True)


def _ledger_period_micros(user, period) -> int:
    from django.db.models import Sum

    from apps.accounts.models import AITokenUsage

    total = (
        AITokenUsage.objects.filter(user=user, created_at__gte=period.start)
        .aggregate(total=Sum("estimated_cost_usd"))["total"]
        or 0
    )
    return int(round(float(total) * 1_000_000))


def _dispatch_notify(user_id, ntype: str) -> None:
    try:
        from apps.metering.tasks import notify_cap_threshold

        notify_cap_threshold.delay(str(user_id), ntype)
    except Exception:
        logger.debug("cap notification dispatch failed", exc_info=True)
