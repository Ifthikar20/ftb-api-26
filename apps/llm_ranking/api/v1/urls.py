from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:website_id>/audits/", views.LLMRankingAuditListView.as_view(), name="llm-ranking-list"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/", views.LLMRankingAuditDetailView.as_view(), name="llm-ranking-detail"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/breakdown/", views.LLMRankingProviderBreakdownView.as_view(), name="llm-ranking-breakdown"),
    path("<uuid:website_id>/audits/<uuid:audit_id>/recommendations/", views.LLMRankingRecommendationsView.as_view(), name="llm-ranking-recommendations"),
    path("<uuid:website_id>/history/", views.LLMRankingHistoryView.as_view(), name="llm-ranking-history"),
]
