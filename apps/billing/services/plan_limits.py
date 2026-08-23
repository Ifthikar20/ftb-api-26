"""Feature-gating helpers that resolve a user's plan and check limits."""

from django.conf import settings

from core.utils.constants import PLAN_LIMITS, Plan, SubscriptionStatus


def plan_for_subscription(sub) -> str:
    """Resolve a Subscription row (or None) to the plan it grants.

    Prefer this over ``current_plan_for`` when you already hold the row
    — ``getattr(user, "subscription")`` caches misses on the instance,
    so a row created or synced mid-request would otherwise be invisible.
    """
    if sub is not None and sub.status in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
    ):
        plan = _LEGACY_MAP.get(sub.plan, sub.plan)
        if plan in (Plan.PRO, Plan.BUSINESS):
            return plan
        return Plan.PRO  # active sub on an unrecognized value: honor payment
    return Plan.FREE


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
    return plan_for_subscription(sub)

# Legacy plan → live-tier mapping (Free / Pro $45 self-serve / Business custom)
_LEGACY_MAP = {
    "individual": Plan.PRO,
    "starter": Plan.PRO,
    "growth": Plan.PRO,
    "scale": Plan.BUSINESS,
    "team": Plan.BUSINESS,
    "enterprise": Plan.BUSINESS,
}


def is_paying(user) -> bool:
    """Provider-backed payment gate used for paywall routing.

    ACTIVE always counts; TRIALING counts only when a Polar subscription
    backs it (card on file, auto-converts). Deliberately stricter than
    ``current_plan_for``, which grants the tier for any ACTIVE/TRIALING
    row.
    """
    sub = getattr(user, "subscription", None) if user is not None else None
    if sub is None:
        return False
    if sub.status == SubscriptionStatus.ACTIVE:
        return True
    return bool(sub.status == SubscriptionStatus.TRIALING and sub.polar_subscription_id)


def _resolve_plan_key(user):
    """Resolve the user's effective plan to a PLAN_LIMITS key."""
    # Paywall off: everyone gets the top tier so no feature or numeric
    # limit blocks them.
    if not settings.PAYWALL_ENABLED:
        return Plan.BUSINESS
    # System callers and anonymous users keep the Pro-tier fallback that
    # the old ``user.plan`` default provided.
    if user is None or not getattr(user, "pk", None):
        return Plan.PRO
    # Enterprise org members inherit the org's manually provisioned plan
    # (Business has no self-serve checkout). Mirrors User.effective_plan's
    # org branch WITHOUT its personal ``user.plan`` fallback, which
    # defaults to a paid tier and leaked paid features to unsubscribed
    # accounts.
    if hasattr(user, "org_memberships"):
        org = getattr(user, "_org_cache", None)
        if org is None:
            membership = user.org_memberships.select_related("organization").first()
            if membership:
                org = membership.organization
                user._org_cache = org
        if org is not None:
            return _LEGACY_MAP.get(org.plan, org.plan)
    return current_plan_for(user)


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
