"""Feature-gating helpers that resolve a user's plan and check limits."""

from core.utils.constants import PLAN_LIMITS, Plan

# Legacy plan → 2-tier mapping
_LEGACY_MAP = {
    "starter": Plan.INDIVIDUAL,
    "growth": Plan.INDIVIDUAL,
    "free": Plan.INDIVIDUAL,
    "scale": Plan.ENTERPRISE,
    "team": Plan.ENTERPRISE,
    "business": Plan.ENTERPRISE,
}


def _resolve_plan_key(user):
    """Resolve the user's effective plan to a PLAN_LIMITS key."""
    plan_key = getattr(user, "effective_plan", None) or getattr(user, "plan", "individual")
    # Map legacy names
    plan_key = _LEGACY_MAP.get(plan_key, plan_key)
    return plan_key


def get_limits(user):
    """Return the PLAN_LIMITS dict for a user's effective plan."""
    plan_key = _resolve_plan_key(user)
    return PLAN_LIMITS.get(plan_key, PLAN_LIMITS[Plan.INDIVIDUAL])


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
