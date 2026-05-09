"""URL routes for the brand_vault REST API."""
from django.urls import path

from . import views

urlpatterns = [
    path(
        "websites/<uuid:website_id>/facts/",
        views.WebsiteFactsView.as_view(),
        name="brand-vault-website-facts",
    ),
    path(
        "websites/<uuid:website_id>/extract/",
        views.WebsiteExtractView.as_view(),
        name="brand-vault-website-extract",
    ),
    path(
        "websites/<uuid:website_id>/stats/",
        views.WebsiteStatsView.as_view(),
        name="brand-vault-website-stats",
    ),
    path(
        "facts/<uuid:fact_id>/",
        views.FactDetailView.as_view(),
        name="brand-vault-fact-detail",
    ),
    path(
        "facts/<uuid:fact_id>/approve/",
        views.FactApproveView.as_view(),
        name="brand-vault-fact-approve",
    ),
    path(
        "facts/<uuid:fact_id>/reject/",
        views.FactRejectView.as_view(),
        name="brand-vault-fact-reject",
    ),
    path(
        "facts/<uuid:fact_id>/edit/",
        views.FactEditView.as_view(),
        name="brand-vault-fact-edit",
    ),
    path(
        "websites/<uuid:website_id>/facts/import/",
        views.WebsiteFactsImportView.as_view(),
        name="brand-vault-website-facts-import",
    ),
    path(
        "websites/<uuid:website_id>/facts/import-csv/",
        views.WebsiteFactsImportCSVView.as_view(),
        name="brand-vault-website-facts-import-csv",
    ),
    path(
        "websites/<uuid:website_id>/tone-samples/",
        views.WebsiteToneSamplesView.as_view(),
        name="brand-vault-website-tone-samples",
    ),
]
