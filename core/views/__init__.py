"""Reusable DRF view base classes for the FTB API.

The vast majority of our endpoints are authenticated, multi-tenant, and
website-scoped. Before this module each view re-implemented:

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        ...

That pattern shows up in 89+ places. Subclassing :class:`TenantScopedAPIView`
collapses it to ``website = self.get_website(website_id)`` and removes the
``permission_classes`` line entirely. Use these bases for any new website-scoped
endpoint and migrate existing ones opportunistically.
"""

from core.views.base import (  # noqa: F401
    TenantScopedAPIView,
    TenantScopedListAPIView,
)
