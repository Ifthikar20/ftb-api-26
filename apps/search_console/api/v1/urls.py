from django.urls import path

from apps.search_console.api.v1 import views

urlpatterns = [
    # OAuth callback (unauthenticated; trust = signed state)
    path("oauth/callback/", views.GscOAuthCallbackView.as_view(), name="gsc-oauth-callback"),

    # Connection management
    path("<uuid:website_id>/connect/", views.GscConnectStartView.as_view(), name="gsc-connect"),
    path("<uuid:website_id>/status/", views.GscStatusView.as_view(), name="gsc-status"),
    path("<uuid:website_id>/properties/", views.GscPropertiesView.as_view(), name="gsc-properties"),
    path("<uuid:website_id>/property/", views.GscSelectPropertyView.as_view(), name="gsc-select-property"),
    path("<uuid:website_id>/connection/", views.GscDisconnectView.as_view(), name="gsc-disconnect"),

    # Data
    path("<uuid:website_id>/summary/", views.GscSummaryView.as_view(), name="gsc-summary"),
    path("<uuid:website_id>/timeseries/", views.GscTimeseriesView.as_view(), name="gsc-timeseries"),
    path("<uuid:website_id>/queries/", views.GscQueriesView.as_view(), name="gsc-queries"),
    path("<uuid:website_id>/pages/", views.GscPagesView.as_view(), name="gsc-pages"),
]
