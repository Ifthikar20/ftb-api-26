from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:website_id>/audits/", views.LLMRankingAuditListView.as_view(), name="llm-ranking-list"),
    path("<uuid:website_id>/preview-prompts/", views.LLMRankingPreviewPromptsView.as_view(), name="llm-ranking-preview-prompts"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/", views.LLMRankingAuditDetailView.as_view(), name="llm-ranking-detail"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/run/", views.LLMRankingAuditRunView.as_view(), name="llm-ranking-run"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/breakdown/", views.LLMRankingProviderBreakdownView.as_view(), name="llm-ranking-breakdown"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/recommendations/", views.LLMRankingRecommendationsView.as_view(), name="llm-ranking-recommendations"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/prompts/", views.LLMRankingPromptResultsView.as_view(), name="llm-ranking-prompt-results"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/providers/<str:provider>/", views.LLMRankingProviderDetailView.as_view(), name="llm-ranking-provider-detail"),
    path("<uuid:website_id>/usage/", views.LLMRankingUsageView.as_view(), name="llm-ranking-usage"),
    path("<uuid:website_id>/history/", views.LLMRankingHistoryView.as_view(), name="llm-ranking-history"),
    path("<uuid:website_id>/schedule/", views.LLMRankingScheduleView.as_view(), name="llm-ranking-schedule"),
]
