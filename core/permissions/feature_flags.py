from .rbac import PLAN_FEATURES


def user_has_feature(user, feature: str) -> bool:
    """Check if a user's plan includes a specific feature."""
    plan = getattr(user, "plan", "starter")
    return feature in PLAN_FEATURES.get(plan, [])


def get_competitor_limit(user) -> int:
    """Return the number of competitors the user's plan allows."""
    plan = getattr(user, "plan", "starter")
    limits = {"starter": 3, "growth": 10, "scale": 50}
    return limits.get(plan, 3)


def get_team_member_limit(user) -> int:
    """Return the number of team members the user's plan allows."""
    plan = getattr(user, "plan", "starter")
    limits = {"starter": 1, "growth": 5, "scale": 9999}
    return limits.get(plan, 1)
