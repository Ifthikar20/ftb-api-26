"""
Unified AI token usage tracking.

Provides a single function `record_usage()` that all AI call sites use to log
their token consumption. This enables centralized monitoring and billing.

The AITokenUsage model lives in apps.accounts.models but is accessed through
this module for convenience.
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Pricing (per 1M tokens) ──
# Updated April 2025 — https://docs.anthropic.com/en/docs/about-claude/models
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # Fallback for unknown models
    "default": {"input": 3.00, "output": 15.00},
}


def _estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated USD cost based on model pricing."""
    pricing = PRICING.get(model_name, PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def record_usage(
    *,
    module: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    user=None,
    website=None,
    provider: str = "anthropic",
    duration_ms: int = 0,
    metadata: dict | None = None,
):
    """
    Record an AI API call's token usage.

    Call this after every `client.messages.create()` using `response.usage`.

    Example:
        from core.ai_tracking import record_usage

        response = client.messages.create(...)
        record_usage(
            module="lead_finder",
            model_name="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            user=request.user,
        )
    """
    try:
        from apps.accounts.models import AITokenUsage

        total = input_tokens + output_tokens
        cost = _estimate_cost(model_name, input_tokens, output_tokens)

        AITokenUsage.objects.create(
            user=user,
            website=website,
            module=module,
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            estimated_cost_usd=cost,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        logger.debug(
            "AI usage: %s | %s | %d in + %d out = %d tokens | $%.4f",
            module, model_name, input_tokens, output_tokens, total, cost,
        )
    except Exception as e:
        logger.warning("Failed to record AI token usage: %s", e)


def get_usage_summary(user=None, days=30):
    """Get aggregated AI usage stats for a user over the past N days."""
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDate
    from apps.accounts.models import AITokenUsage

    cutoff = timezone.now() - timedelta(days=days)
    qs = AITokenUsage.objects.filter(created_at__gte=cutoff)
    if user:
        qs = qs.filter(user=user)

    # Overall totals
    totals = qs.aggregate(
        total_calls=Count("id"),
        total_input=Sum("input_tokens"),
        total_output=Sum("output_tokens"),
        total_tokens=Sum("total_tokens"),
        total_cost=Sum("estimated_cost_usd"),
    )

    # Per-module breakdown
    by_module = list(
        qs.values("module").annotate(
            calls=Count("id"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        ).order_by("-tokens")
    )

    # Per-model breakdown
    by_model = list(
        qs.values("model_name").annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        ).order_by("-tokens")
    )

    # Daily trend (last N days)
    daily = list(
        qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        )
        .order_by("day")
    )

    return {
        "period_days": days,
        "totals": {
            "calls": totals["total_calls"] or 0,
            "input_tokens": totals["total_input"] or 0,
            "output_tokens": totals["total_output"] or 0,
            "total_tokens": totals["total_tokens"] or 0,
            "estimated_cost_usd": float(totals["total_cost"] or 0),
        },
        "by_module": by_module,
        "by_model": by_model,
        "daily": daily,
    }
