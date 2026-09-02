"""Organization-level permission classes.

Membership is resolved once per request and cached on it; views read the
resolved membership via ``request.org_membership`` afterwards instead of
re-querying.
"""
from django.conf import settings
from rest_framework.permissions import BasePermission

from core.permissions.rbac import role_at_least


def org_features_enabled() -> bool:
    """The master switch for every business/organization flow."""
    return bool(getattr(settings, "ORG_FEATURES_ENABLED", False))


class OrgFeaturesGate:
    """View mixin: the whole endpoint 404s while business flows are off.

    404, not 403 — a disabled product surface should be indistinguishable
    from one that never existed. Runs in DRF's ``initial`` hook so it
    applies before any permission class or handler.
    """

    def initial(self, request, *args, **kwargs):
        if not org_features_enabled():
            from core.exceptions import ResourceNotFound

            raise ResourceNotFound("Not found.")
        super().initial(request, *args, **kwargs)


def resolve_membership(request):
    """The requester's org membership row, or None. Cached per-request."""
    if not hasattr(request, "_org_membership_cache"):
        user = request.user
        membership = None
        if user and user.is_authenticated:
            membership = (
                user.org_memberships.select_related("organization")
                .order_by("created_at")
                .first()
            )
        request._org_membership_cache = membership
    return request._org_membership_cache


class IsOrgMember(BasePermission):
    """Any accepted member of an organization."""

    message = "You are not a member of an organization."

    def has_permission(self, request, view):
        membership = resolve_membership(request)
        if membership is None:
            return False
        request.org_membership = membership
        return True


class IsOrgAdmin(IsOrgMember):
    """Admin or owner of the organization."""

    message = "This action requires an organization admin."
    required_role = "admin"

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return role_at_least(request.org_membership.role, self.required_role)


class IsOrgOwner(IsOrgAdmin):
    """The organization owner alone."""

    message = "This action requires the organization owner."
    required_role = "owner"
