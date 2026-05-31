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
        "websites/<uuid:website_id>/urls/",
        views.WebsiteUrlsView.as_view(),
        name="citations-website-urls",
    ),
    path(
        "websites/<uuid:website_id>/urls/detail/",
        views.WebsiteUrlDetailView.as_view(),
        name="citations-website-url-detail",
    ),
    path(
        "websites/<uuid:website_id>/chats/<uuid:result_id>/",
        views.WebsiteChatDetailView.as_view(),
        name="citations-website-chat-detail",
    ),
    path(
        "source-influence/global/",
        views.GlobalSourceInfluenceView.as_view(),
        name="citations-global-influence",
    ),
]
