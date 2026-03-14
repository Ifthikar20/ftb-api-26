from rest_framework.permissions import BasePermission

ROLE_HIERARCHY = {
    "owner": 100,
    "admin": 80,
    "editor": 60,
    "viewer": 20,
}

# Base platform features per tier (non-integration features)
_BASE_PLAN_FEATURES = {
    "starter": [
        "audit", "basic_analytics", "basic_leads", "competitors_3",
    ],
    "growth": [
        "audit", "full_analytics", "ai_strategy", "ai_chat", "content_calendar",
        "advanced_leads", "competitors_10", "team_5",
    ],
    "scale": [
        "audit", "full_analytics", "ai_strategy", "ai_chat", "content_calendar",
        "advanced_leads", "competitors_50", "team_unlimited", "api_access",
        "white_label", "dedicated_support",
    ],
}


def _build_plan_features() -> dict[str, list[str]]:
    """Build PLAN_FEATURES by merging base features with integration entitlements."""
    from core.integrations import get_registry
    registry = get_registry()
    result = {}
    for plan, base_features in _BASE_PLAN_FEATURES.items():
        result[plan] = list(base_features) + registry.feature_keys_for(plan)
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
        user_plan = getattr(request.user, "plan", "starter")
        return self.required_feature in PLAN_FEATURES.get(user_plan, [])
