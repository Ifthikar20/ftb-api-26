"""URL routes for the prompt_library REST API."""
from django.urls import path

from . import views

urlpatterns = [
    path("industries/", views.IndustryListView.as_view(), name="prompt-library-industries"),
    path(
        "industries/<slug:slug>/trends/",
        views.IndustryTrendView.as_view(),
        name="prompt-library-industry-trends",
    ),
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
    path(
        "websites/<uuid:website_id>/brand-prompts/",
        views.WebsiteBrandPromptsView.as_view(),
        name="prompt-library-brand-prompts",
    ),
    path(
        "brand-prompts/<uuid:brand_prompt_id>/",
        views.BrandPromptDetailView.as_view(),
        name="prompt-library-brand-prompt-detail",
    ),
]
