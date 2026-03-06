from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:website_id>/overview/", views.AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("<uuid:website_id>/pages/", views.TopPagesView.as_view(), name="analytics-pages"),
    path("<uuid:website_id>/sources/", views.TrafficSourcesView.as_view(), name="analytics-sources"),
    path("<uuid:website_id>/realtime/", views.RealtimeView.as_view(), name="analytics-realtime"),
]
