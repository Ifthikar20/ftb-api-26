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
        "prompts/auto-template/",
        views.PromptAutoTemplateView.as_view(),
        name="prompt-library-auto-template",
    ),
    path(
        "prompts/search-sources/",
        views.PromptSearchSourcesView.as_view(),
        name="prompt-library-search-sources",
    ),
    path(
        "prompts/synthesize/",
        views.PromptSynthesizeView.as_view(),
        name="prompt-library-synthesize",
    ),
    path(
        "prompts/generate-from-context/",
        views.PromptGenerateFromContextView.as_view(),
        name="prompt-library-generate-from-context",
    ),
    path(
        "prompts/<uuid:prompt_id>/preview/",
        views.PromptPreviewView.as_view(),
        name="prompt-library-prompt-preview",
    ),
    path(
        "prompts/<uuid:prompt_id>/effectiveness/",
        views.PromptEffectivenessView.as_view(),
        name="prompt-library-prompt-effectiveness",
    ),
    path(
        "prompts/<uuid:prompt_id>/smoke-test/",
        views.PromptSmokeTestView.as_view(),
        name="prompt-library-prompt-smoke-test",
    ),
    path(
        "prompts/<uuid:prompt_id>/enable/",
        views.PromptToggleView.as_view(),
        {"action": "enable"},
        name="prompt-library-prompt-enable",
    ),
    path(
        "prompts/<uuid:prompt_id>/disable/",
        views.PromptToggleView.as_view(),
        {"action": "disable"},
        name="prompt-library-prompt-disable",
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
        "websites/<uuid:website_id>/prompts/",
        views.WebsitePromptCreateView.as_view(),
        name="prompt-library-website-prompts",
    ),
    path(
        "websites/<uuid:website_id>/variables/",
        views.WebsiteVariablesView.as_view(),
        name="prompt-library-website-variables",
    ),
    path(
        "brand-prompts/<uuid:brand_prompt_id>/",
        views.BrandPromptDetailView.as_view(),
        name="prompt-library-brand-prompt-detail",
    ),
]
