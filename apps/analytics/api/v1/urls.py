from django.urls import path
from . import views
from . import keyword_views

urlpatterns = [
    path("<uuid:website_id>/overview/", views.AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("<uuid:website_id>/pages/", views.TopPagesView.as_view(), name="analytics-pages"),
    path("<uuid:website_id>/sources/", views.TrafficSourcesView.as_view(), name="analytics-sources"),
    path("<uuid:website_id>/realtime/", views.RealtimeView.as_view(), name="analytics-realtime"),
    path("<uuid:website_id>/heatmap/", views.HeatmapView.as_view(), name="analytics-heatmap"),
    path("<uuid:website_id>/keywords/", keyword_views.KeywordListCreateView.as_view(), name="keywords-list-create"),
    path("<uuid:website_id>/keywords/<uuid:keyword_id>/history/", keyword_views.KeywordHistoryView.as_view(), name="keyword-history"),
]
