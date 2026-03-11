from django.urls import path
from . import views
from . import keyword_views
from . import analytics_views

urlpatterns = [
    # Existing
    path("<uuid:website_id>/overview/", views.AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("<uuid:website_id>/pages/", views.TopPagesView.as_view(), name="analytics-pages"),
    path("<uuid:website_id>/sources/", views.TrafficSourcesView.as_view(), name="analytics-sources"),
    path("<uuid:website_id>/realtime/", views.RealtimeView.as_view(), name="analytics-realtime"),
    path("<uuid:website_id>/heatmap/", views.HeatmapView.as_view(), name="analytics-heatmap"),
    path("<uuid:website_id>/keywords/trending/", keyword_views.TrendingKeywordsView.as_view(), name="keywords-trending"),
    path("<uuid:website_id>/keywords/scores/", keyword_views.KeywordScoresView.as_view(), name="keywords-scores"),
    path("<uuid:website_id>/keywords/suggestions/", keyword_views.KeywordSuggestionsView.as_view(), name="keywords-suggestions"),
    path("<uuid:website_id>/keywords/interest/", keyword_views.KeywordInterestView.as_view(), name="keywords-interest"),
    path("<uuid:website_id>/keywords/", keyword_views.KeywordListCreateView.as_view(), name="keywords-list-create"),
    path("<uuid:website_id>/keywords/<uuid:keyword_id>/history/", keyword_views.KeywordHistoryView.as_view(), name="keyword-history"),

    # New — Advanced Analytics
    path("<uuid:website_id>/chart/", analytics_views.ChartDataView.as_view(), name="analytics-chart"),
    path("<uuid:website_id>/devices/", analytics_views.DeviceBreakdownView.as_view(), name="analytics-devices"),
    path("<uuid:website_id>/countries/", analytics_views.CountryBreakdownView.as_view(), name="analytics-countries"),
    path("<uuid:website_id>/funnels/", analytics_views.FunnelListCreateView.as_view(), name="analytics-funnels"),
    path("<uuid:website_id>/funnels/<int:funnel_id>/calculate/", analytics_views.FunnelCalculateView.as_view(), name="analytics-funnel-calculate"),
    path("<uuid:website_id>/retention/", analytics_views.RetentionView.as_view(), name="analytics-retention"),
    path("<uuid:website_id>/retention/curve/", analytics_views.RetentionCurveView.as_view(), name="analytics-retention-curve"),
    path("<uuid:website_id>/flows/", analytics_views.FlowView.as_view(), name="analytics-flows"),
    path("<uuid:website_id>/entry-exit/", analytics_views.EntryExitPagesView.as_view(), name="analytics-entry-exit"),
    path("<uuid:website_id>/journeys/", analytics_views.VisitorJourneysView.as_view(), name="analytics-journeys"),
    path("<uuid:website_id>/visitors/", analytics_views.VisitorListView.as_view(), name="analytics-visitors"),
    path("<uuid:website_id>/visitors/<uuid:visitor_id>/timeline/", analytics_views.VisitorTimelineView.as_view(), name="analytics-visitor-timeline"),
    path("<uuid:website_id>/insights/", analytics_views.AIInsightsView.as_view(), name="analytics-insights"),
    path("<uuid:website_id>/live/", analytics_views.LiveEventsView.as_view(), name="analytics-live"),
]
