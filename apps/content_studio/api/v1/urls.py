"""URL routes for the content_studio REST API."""
from django.urls import path

from . import views

urlpatterns = [
    path(
        "websites/<uuid:website_id>/briefs/",
        views.WebsiteBriefsView.as_view(),
        name="content-studio-website-briefs",
    ),
    path(
        "briefs/<uuid:brief_id>/",
        views.BriefDetailView.as_view(),
        name="content-studio-brief-detail",
    ),
    path(
        "briefs/<uuid:brief_id>/draft/",
        views.BriefDraftView.as_view(),
        name="content-studio-brief-draft",
    ),
    path(
        "briefs/<uuid:brief_id>/skip/",
        views.BriefSkipView.as_view(),
        name="content-studio-brief-skip",
    ),
    path(
        "drafts/<uuid:draft_id>/",
        views.DraftDetailView.as_view(),
        name="content-studio-draft-detail",
    ),
    path(
        "drafts/<uuid:draft_id>/regenerate/",
        views.DraftRegenerateView.as_view(),
        name="content-studio-draft-regenerate",
    ),
    path(
        "drafts/<uuid:draft_id>/approve/",
        views.DraftApproveView.as_view(),
        name="content-studio-draft-approve",
    ),
]
