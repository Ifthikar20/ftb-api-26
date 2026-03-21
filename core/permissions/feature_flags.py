from .rbac import PLAN_FEATURES


def user_has_feature(user, feature: str) -> bool:
    """Check if a user's plan includes a specific feature."""
    plan = getattr(user, "plan", "starter")
    return feature in PLAN_FEATURES.get(plan, [])


def get_competitor_limit(user) -> int:
    """Return the number of competitors the user's plan allows."""
    from core.integrations import get_registry
    registry = get_registry()
    return registry.get_limit(user, "semrush", "competitors", default=3)


def get_team_member_limit(user) -> int:
    """Return the number of team members the user's plan allows."""
    plan = getattr(user, "plan", "starter")
    limits = {"starter": 1, "growth": 5, "scale": 9999}
    return limits.get(plan, 1)


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
