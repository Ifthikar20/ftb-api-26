"""URL routes for the prompt_library REST API."""
from django.urls import path

from . import views

urlpatterns = [
    path("industries/", views.IndustryListView.as_view(), name="prompt-library-industries"),
    path("prompts/", views.PromptListView.as_view(), name="prompt-library-prompts"),
    path(
        "prompts/preview-sample/",
        views.PreviewSampleView.as_view(),
        name="prompt-library-preview-sample",
    ),
    path(
        "audits/<uuid:audit_id>/use-library-sample/",
        views.UseLibrarySampleView.as_view(),
        name="prompt-library-use-sample",
    ),
    path(
        "audits/<uuid:audit_id>/sample/",
        views.GetAuditSampleView.as_view(),
        name="prompt-library-audit-sample",
    ),
]
