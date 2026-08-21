"""Feature-gating helpers that resolve a user's plan and check limits."""

from django.conf import settings

from core.utils.constants import PLAN_LIMITS, Plan, SubscriptionStatus


def current_plan_for(user) -> str:
    """The plan the account is ACTUALLY on, resolved from subscription
    status — the single source of truth for billing-facing surfaces.

    An active or trialing subscription grants its plan; everything else
    (no subscription, canceled, past_due beyond grace) is the FREE plan.
    The denormalized ``user.plan`` value is deliberately not consulted:
    it defaults to a paid tier and historically leaked paid allowances
    to unsubscribed accounts.
    """
    if user is None:
        return Plan.FREE
    try:
        sub = getattr(user, "subscription", None)
    except Exception:
        sub = None
    if sub is not None and sub.status in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
    ):
        plan = _LEGACY_MAP.get(sub.plan, sub.plan)
        if plan in (Plan.PRO, Plan.BUSINESS):
            return plan
        return Plan.PRO  # active sub on an unrecognized value: honor payment
    return Plan.FREE

# Legacy plan → live-tier mapping (Free / Pro $45 self-serve / Business custom)
_LEGACY_MAP = {
    "individual": Plan.PRO,
    "starter": Plan.PRO,
    "growth": Plan.PRO,
    "scale": Plan.BUSINESS,
    "team": Plan.BUSINESS,
    "enterprise": Plan.BUSINESS,
}


def _resolve_plan_key(user):
    """Resolve the user's effective plan to a PLAN_LIMITS key."""
    # Paywall off: everyone gets the top tier so no feature or numeric
    # limit blocks them.
    if not settings.PAYWALL_ENABLED:
        return Plan.BUSINESS
    plan_key = getattr(user, "effective_plan", None) or getattr(user, "plan", "pro")
    # Map legacy names
    plan_key = _LEGACY_MAP.get(plan_key, plan_key)
    return plan_key


def get_limits(user):
    """Return the PLAN_LIMITS dict for a user's effective plan."""
    plan_key = _resolve_plan_key(user)
    return PLAN_LIMITS.get(plan_key, PLAN_LIMITS[Plan.PRO])


def check_feature(user, feature_key):
    """Return True if the user's plan includes the boolean feature."""
    limits = get_limits(user)
    value = limits.get(feature_key)
    if isinstance(value, bool):
        return value
    # Numeric limits: -1 means unlimited, otherwise check > 0
    if isinstance(value, int):
        return value != 0
    return False


def get_numeric_limit(user, feature_key):
    """Return the numeric limit (or -1 for unlimited)."""
    limits = get_limits(user)
    return limits.get(feature_key, 0)


def is_within_limit(user, feature_key, current_usage):
    """Check whether current usage is within the plan limit."""
    limit = get_numeric_limit(user, feature_key)
    if limit == -1:
        return True  # unlimited
    return current_usage < limit


def get_segment(user):
    """Return the user's segment (individual or enterprise)."""
    limits = get_limits(user)
    return limits.get("segment", "individual")


def get_visible_tabs(user):
    """Return the list of visible sidebar tabs for the user's plan."""
    limits = get_limits(user)
    return limits.get("tabs", [])
