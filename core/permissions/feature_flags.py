from django.conf import settings

from .rbac import PLAN_FEATURES


def user_has_feature(user, feature: str) -> bool:
    """Check if a user's plan includes a specific feature."""
    if not settings.PAYWALL_ENABLED:
        return True
    from core.utils.constants import legacy_tier_key
    plan = getattr(user, "plan", "pro")
    features = PLAN_FEATURES.get(plan) or PLAN_FEATURES.get(legacy_tier_key(plan), [])
    return feature in features


def get_competitor_limit(user) -> int:
    """Return the number of competitors the user's plan allows."""
    from core.integrations import get_registry
    registry = get_registry()
    return registry.get_limit(user, "semrush", "competitors", default=3)


def get_team_member_limit(user) -> int:
    """Return the number of team members the user's plan allows.

    Reads the canonical PLAN_LIMITS table (via plan_limits) instead of a
    private copy, so live and legacy plan names resolve identically.
    """
    if not settings.PAYWALL_ENABLED:
        return 9999
    from apps.billing.services.plan_limits import get_limits
    raw = get_limits(user).get("team_members", 1)
    return 9999 if raw == -1 else int(raw)


def user_has_integration(user, integration_name: str) -> bool:
    """Check if a user's plan allows a specific integration."""
    from core.integrations import get_registry
    return get_registry().check_entitlement(user, integration_name)


def get_integration_limit(user, integration_name: str, limit_name: str, default=None):
    """Get a specific limit for a user's plan and integration.

    Example:
        max_endpoints = get_integration_limit(user, "webhooks", "max_endpoints", default=0)
    """
    from core.integrations import get_registry
    return get_registry().get_limit(user, integration_name, limit_name, default)
