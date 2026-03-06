from rest_framework.permissions import BasePermission

ROLE_HIERARCHY = {
    "owner": 100,
    "admin": 80,
    "editor": 60,
    "viewer": 20,
}

PLAN_FEATURES = {
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
