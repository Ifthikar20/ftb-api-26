from django.urls import path

from . import views

urlpatterns = [
    path("provider-health/", views.LLMRankingProviderHealthView.as_view(), name="llm-ranking-provider-health"),
    path("scan-domain/", views.ScanDomainView.as_view(), name="llm-ranking-scan-domain"),
    path("suggest-context/", views.SuggestAuditContextView.as_view(), name="llm-ranking-suggest-context"),
    path("<uuid:website_id>/audits/", views.LLMRankingAuditListView.as_view(), name="llm-ranking-list"),
    path("<uuid:website_id>/preview-prompts/", views.LLMRankingPreviewPromptsView.as_view(), name="llm-ranking-preview-prompts"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/", views.LLMRankingAuditDetailView.as_view(), name="llm-ranking-detail"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/run/", views.LLMRankingAuditRunView.as_view(), name="llm-ranking-run"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/breakdown/", views.LLMRankingProviderBreakdownView.as_view(), name="llm-ranking-breakdown"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/recommendations/", views.LLMRankingRecommendationsView.as_view(), name="llm-ranking-recommendations"),
    path("<uuid:website_id>/history/", views.LLMRankingHistoryView.as_view(), name="llm-ranking-history"),
    path("<uuid:website_id>/schedule/", views.LLMRankingScheduleView.as_view(), name="llm-ranking-schedule"),
]
