from django.urls import path

from . import views

urlpatterns = [
    # Per-website lead source configuration
    path("<uuid:website_id>/sources/", views.SocialLeadSourceListView.as_view(), name="social-source-list"),
    path("<uuid:website_id>/sources/<uuid:source_id>/", views.SocialLeadSourceDetailView.as_view(), name="social-source-detail"),

    # Social leads list
    path("<uuid:website_id>/leads/", views.SocialLeadListView.as_view(), name="social-lead-list"),

    # Platform-specific sync / import
    path("<uuid:website_id>/sources/<uuid:source_id>/sync/linkedin/", views.LinkedInSyncView.as_view(), name="social-linkedin-sync"),
    path("<uuid:website_id>/import/x/", views.XCSVImportView.as_view(), name="social-x-import"),

    # Webhooks (no auth — verified via token/signature)
    path("webhook/facebook/", views.FacebookWebhookView.as_view(), name="social-facebook-webhook"),
]
