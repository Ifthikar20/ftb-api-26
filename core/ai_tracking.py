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
# Every model id reachable from apps.llm_ranking.providers.MODEL_VARIANTS must
# have an entry here, or its spend is booked at ``default`` and the per-user
# spend cap silently under- or over-counts. ``test_pricing_covers_variants``
# enforces that; do not add a variant without adding its price.
#
# Sources:
#   Anthropic  — https://docs.anthropic.com/en/docs/about-claude/models
#   OpenAI     — https://openai.com/api/pricing
#   Google     — https://ai.google.dev/gemini-api/docs/pricing
#   Perplexity — https://docs.perplexity.ai/docs/pricing
#   xAI        — https://docs.x.ai/docs/models
#   DeepSeek   — https://api-docs.deepseek.com/quick_start/pricing
PRICING = {
    # ── Anthropic ──
    "claude-opus-5": {"input": 5.00, "output": 25.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    # Haiku 4.5 is the highest-volume model in the system — it backs both the
    # default `claude` provider and every extraction call — so an error here
    # skews the whole ledger. Was $0.80/$4.00, which understated it by 25%.
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # ── OpenAI ──
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    # ── Google ──
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},  # UNVERIFIED
    # ── Perplexity (Sonar online models) ──
    "llama-3.1-sonar-small-128k-online": {"input": 0.20, "output": 0.20},
    "llama-3.1-sonar-large-128k-online": {"input": 1.00, "output": 1.00},
    # ── xAI ── UNVERIFIED
    "grok-4": {"input": 3.00, "output": 15.00},
    "grok-3": {"input": 3.00, "output": 15.00},
    # ── DeepSeek ── UNVERIFIED
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # Fallback for unknown models. Deliberately expensive: over-counting spend
    # trips the cap early, which is recoverable; under-counting bills the user
    # for a runaway, which is not. `_estimate_cost` warns when this is hit.
    "default": {"input": 3.00, "output": 15.00},
}

# Entries tagged UNVERIFIED above were added from memory because the vendor
# pricing pages are unreachable from the build environment (egress proxy
# blocks ai.google.dev, docs.x.ai, api-docs.deepseek.com). They are far
# closer than the $3/$15 fallback they replace, but check them against the
# live pricing pages before using this ledger to set customer rates.
UNVERIFIED_PRICES = frozenset({
    "gemini-2.0-flash", "grok-4", "grok-3", "deepseek-chat", "deepseek-reasoner",
})


# Map known model names to canonical provider keys used in AITokenUsage.provider.
MODEL_PROVIDER = {
    "claude-opus-5": "anthropic",
    "claude-sonnet-5": "anthropic",
    "claude-opus-4-8": "anthropic",
    "claude-sonnet-4-6": "anthropic",
    "claude-sonnet-4-5-20250929": "anthropic",
    "claude-sonnet-4-20250514": "anthropic",
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-haiku-4-5-20251001": "anthropic",
    "claude-haiku-4-5": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "gpt-4o-mini": "openai",
    "gpt-4o": "openai",
    "gpt-4-turbo": "openai",
    "gemini-1.5-flash": "google",
    "gemini-1.5-pro": "google",
    "gemini-2.0-flash": "google",
    "llama-3.1-sonar-small-128k-online": "perplexity",
    "llama-3.1-sonar-large-128k-online": "perplexity",
    "grok-4": "xai",
    "grok-3": "xai",
    "deepseek-chat": "deepseek",
    "deepseek-reasoner": "deepseek",
}


# Model names already reported as unpriced. Warning once per name per process
# keeps the signal visible in logs without emitting a line on every call.
_WARNED_UNPRICED: set[str] = set()


def _estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated USD cost based on model pricing.

    An unknown model falls back to ``PRICING["default"]`` rather than raising,
    because a missing price must never break a working audit. It does warn —
    once per model name — so the gap surfaces in logs instead of silently
    mis-billing every call. The CI guard in ``core/tests/test_pricing.py``
    catches this for models reachable from ``MODEL_VARIANTS``; the warning is
    the backstop for ids injected at runtime via ``LLM_CLAUDE_MODEL`` or
    ``LLM_EXTRACTION_MODEL``.
    """
    pricing = PRICING.get(model_name)
    if pricing is None:
        pricing = PRICING["default"]
        if model_name not in _WARNED_UNPRICED:
            _WARNED_UNPRICED.add(model_name)
            logger.warning(
                "No PRICING entry for model %r — billing at the default "
                "$%.2f/$%.2f per 1M tokens. Spend tracking and the monthly "
                "cost cap will be wrong for this model until it is added.",
                model_name, pricing["input"], pricing["output"],
            )
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
            module="llm_ranking",
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
        # Auto-derive provider when caller leaves the default — keeps every
        # row consistent for the centralized "by provider" rollup.
        if provider == "anthropic" and model_name in MODEL_PROVIDER:
            provider = MODEL_PROVIDER[model_name]

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
    """
    Aggregated AI usage stats across every provider and module for a user.

    Powers the centralized "Overall Usage" panel in Settings. Each row recorded
    via record_usage() — Lead Finder, Messaging, Analytics, LLM Ranking
    (upstream + extraction), Competitor Discovery — rolls into the same totals.
    """
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncDate

    from apps.accounts.models import AITokenUsage

    cutoff = timezone.now() - timedelta(days=days)
    qs = AITokenUsage.objects.filter(created_at__gte=cutoff)
    if user:
        qs = qs.filter(user=user)

    totals = qs.aggregate(
        total_calls=Count("id"),
        total_input=Sum("input_tokens"),
        total_output=Sum("output_tokens"),
        total_tokens=Sum("total_tokens"),
        total_cost=Sum("estimated_cost_usd"),
    )

    by_module = list(
        qs.values("module").annotate(
            calls=Count("id"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        ).order_by("-tokens")
    )

    by_model = list(
        qs.values("model_name").annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        ).order_by("-tokens")
    )

    by_provider = list(
        qs.values("provider").annotate(
            calls=Count("id"),
            tokens=Sum("total_tokens"),
            cost=Sum("estimated_cost_usd"),
        ).order_by("-cost")
    )

    # Role split — bucket every recorded call by metadata.role so the rows
    # add up to the totals row. Rows lacking a role tag (legacy records and
    # call sites that pre-date role tagging) bucket as "upstream".
    by_role_map: dict = {}
    for row in qs.values("metadata", "total_tokens", "estimated_cost_usd"):
        role = (row["metadata"] or {}).get("role") or "upstream"
        bucket = by_role_map.setdefault(
            role, {"role": role, "calls": 0, "tokens": 0, "cost": 0.0},
        )
        bucket["calls"] += 1
        bucket["tokens"] += row["total_tokens"] or 0
        bucket["cost"] += float(row["estimated_cost_usd"] or 0)
    by_role = sorted(by_role_map.values(), key=lambda r: r["cost"], reverse=True)
    for r in by_role:
        r["cost"] = round(r["cost"], 6)

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

    # Cap status — uses User.monthly_ai_cost_cap_usd if set. Compares against
    # the calendar-month-to-date spend, NOT the rolling window above.
    cap_status = _cap_status(user) if user else None

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
        "by_provider": by_provider,
        "by_role": by_role,
        "daily": daily,
        "cap_status": cap_status,
    }


def _cap_status(user):
    """Calendar-month-to-date spend vs the user's monthly cap (if any)."""
    from django.db.models import Sum

    from apps.accounts.models import AITokenUsage

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spent = (
        AITokenUsage.objects
        .filter(user=user, created_at__gte=month_start)
        .aggregate(total=Sum("estimated_cost_usd"))["total"] or 0
    )
    spent = float(spent)
    cap = float(getattr(user, "monthly_ai_cost_cap_usd", 0) or 0)
    return {
        "month_start": month_start.isoformat(),
        "spent_usd": round(spent, 4),
        "cap_usd": cap,
        "pct": round(spent / cap * 100, 1) if cap > 0 else None,
        "exceeded": cap > 0 and spent >= cap,
    }


def month_to_date_cost(user) -> float:
    """Calendar-month-to-date AI cost for a user. Used by per-module cost guards."""
    from django.db.models import Sum

    from apps.accounts.models import AITokenUsage

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = (
        AITokenUsage.objects
        .filter(user=user, created_at__gte=month_start)
        .aggregate(total=Sum("estimated_cost_usd"))["total"] or 0
    )
    return float(total)
