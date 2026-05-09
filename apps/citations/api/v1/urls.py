"""URL routes for the citations REST API."""
from django.urls import path

from . import views

urlpatterns = [
    path(
        "audits/<uuid:audit_id>/citations/",
        views.AuditCitationsView.as_view(),
        name="citations-audit-list",
    ),
    path(
        "audits/<uuid:audit_id>/source-influence/",
        views.AuditSourceInfluenceView.as_view(),
        name="citations-audit-influence",
    ),
    path(
        "websites/<uuid:website_id>/source-influence/",
        views.WebsiteSourceInfluenceView.as_view(),
        name="citations-website-influence",
    ),
    path(
        "websites/<uuid:website_id>/citations/",
        views.WebsiteCitationsView.as_view(),
        name="citations-website-list",
    ),
    path(
        "source-influence/global/",
        views.GlobalSourceInfluenceView.as_view(),
        name="citations-global-influence",
    ),
]
