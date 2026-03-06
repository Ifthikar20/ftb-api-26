from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object owner check — obj must have a `user` or `user_id` field."""

    def has_object_permission(self, request, view, obj):
        user_id = getattr(obj, "user_id", None) or getattr(getattr(obj, "user", None), "id", None)
        return user_id == request.user.id


class IsTeamMember(BasePermission):
    """User must be a team member or owner of the website."""

    def has_object_permission(self, request, view, obj):
        website = getattr(obj, "website", obj)
        if website.user_id == request.user.id:
            return True
        return website.memberships.filter(user=request.user).exists()


class IsPlanAllowed(BasePermission):
    """Check that the user's plan allows this action."""
    required_plan_level = 0

    PLAN_LEVELS = {"starter": 1, "growth": 2, "scale": 3}

    def has_permission(self, request, view):
        user_plan = getattr(request.user, "plan", "starter")
        return self.PLAN_LEVELS.get(user_plan, 0) >= self.required_plan_level
