from rest_framework.permissions import BasePermission

# One ladder for both role vocabularies: the org layer says "member"
# (core.utils.constants.OrgRole), dormant WebsiteMembership rows say
# "editor" — they are the same read-write rank. Before this alias existed,
# ROLE_HIERARCHY.get("member", 0) scored an org member at 0, BELOW viewer.
ROLE_HIERARCHY = {
    "owner": 100,
    "admin": 80,
    "member": 60,
    "editor": 60,  # legacy alias of member
    "viewer": 20,
}


def role_at_least(role: str, required: str) -> bool:
    """True when ``role`` meets or outranks ``required`` on the ladder.

    Unknown strings rank 0 on either side, so an unknown *held* role is
    denied and an unknown *required* role would allow anyone — always pass
    ``required`` from OrgRole/UserRole values.
    """
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(required, 0)

# Base platform features per tier (non-integration features).
# "pro" and "business" are the live plan names; the historical
# starter/growth/scale entries stay for legacy rows.
_BASE_PLAN_FEATURES = {
    "starter": [
        "basic_analytics", "basic_leads", "competitors_3",
    ],
    "growth": [
        "full_analytics",
        "advanced_leads", "competitors_10", "team_5",
    ],
    "scale": [
        "full_analytics",
        "advanced_leads", "competitors_50", "team_unlimited", "api_access",
        "white_label", "dedicated_support",
    ],
    "pro": [
        "full_analytics",
        "advanced_leads", "competitors_25", "team_5", "api_access",
    ],
    "business": [
        "full_analytics",
        "advanced_leads", "competitors_50", "team_unlimited", "api_access",
        "white_label", "dedicated_support",
    ],
}


def _build_plan_features() -> dict[str, list[str]]:
    """Build PLAN_FEATURES by merging base features with integration entitlements."""
    from core.integrations import get_registry
    from core.utils.constants import legacy_tier_key
    registry = get_registry()
    result = {}
    for plan, base_features in _BASE_PLAN_FEATURES.items():
        # Integration tier tables only know starter/growth/scale.
        result[plan] = list(base_features) + registry.feature_keys_for(
            legacy_tier_key(plan)
        )
    return result


# Lazy-loaded to avoid import cycles with Django settings
_plan_features_cache = None


def get_plan_features() -> dict[str, list[str]]:
    global _plan_features_cache
    if _plan_features_cache is None:
        _plan_features_cache = _build_plan_features()
    return _plan_features_cache


# Backwards-compatible module-level access — rebuilt once on first import
class _PlanFeaturesProxy(dict):
    """Lazy dict that builds itself on first access."""
    _loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self.update(get_plan_features())
            self._loaded = True

    def __getitem__(self, key):
        self._ensure_loaded()
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._ensure_loaded()
        return super().get(key, default)

    def __contains__(self, key):
        self._ensure_loaded()
        return super().__contains__(key)

    def items(self):
        self._ensure_loaded()
        return super().items()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def keys(self):
        self._ensure_loaded()
        return super().keys()


PLAN_FEATURES = _PlanFeaturesProxy()


class IsWebsiteOwner(BasePermission):
    """Only the website owner can perform this action."""

    def has_object_permission(self, request, view, obj):
        website = getattr(obj, "website", obj)
        return website.user_id == request.user.id


class HasWebsiteRole(BasePermission):
    """Check user has minimum role for the website."""
    required_role = "viewer"

    def has_object_permission(self, request, view, obj):
        website = getattr(obj, "website", obj)
        membership = website.memberships.filter(user=request.user).first()
        if not membership:
            return website.user_id == request.user.id
        return (
            ROLE_HIERARCHY.get(membership.role, 0)
            >= ROLE_HIERARCHY.get(self.required_role, 0)
        )


class IsAdminRole(HasWebsiteRole):
    required_role = "admin"


class IsEditorRole(HasWebsiteRole):
    required_role = "editor"


class PlanFeatureRequired(BasePermission):
    """Gate features behind plan tiers."""
    required_feature = None

    def has_permission(self, request, view):
        if not self.required_feature:
            return True
        from django.conf import settings
        if not settings.PAYWALL_ENABLED:
            return True
        from core.utils.constants import legacy_tier_key
        user_plan = getattr(request.user, "plan", "pro")
        features = (
            PLAN_FEATURES.get(user_plan)
            or PLAN_FEATURES.get(legacy_tier_key(user_plan), [])
        )
        return self.required_feature in features
