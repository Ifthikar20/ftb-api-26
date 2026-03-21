from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:website_id>/", views.LeadListView.as_view(), name="lead-list"),
    path("<uuid:website_id>/hot/", views.HotLeadsView.as_view(), name="lead-hot"),
    path("<uuid:website_id>/export/", views.LeadExportView.as_view(), name="lead-export"),
    path("<uuid:website_id>/scoring-config/", views.ScoringConfigView.as_view(), name="lead-scoring-config"),
    path("<uuid:website_id>/segments/", views.LeadSegmentListView.as_view(), name="lead-segment-list"),
    path("<uuid:website_id>/segments/<uuid:segment_id>/", views.LeadSegmentDetailView.as_view(), name="lead-segment-detail"),
    path("<uuid:website_id>/<uuid:lead_id>/", views.LeadDetailView.as_view(), name="lead-detail"),
    path("<uuid:website_id>/<uuid:lead_id>/note/", views.LeadNoteView.as_view(), name="lead-note"),
    path("<uuid:website_id>/ai-search/", views.AILeadFinderView.as_view(), name="lead-ai-search"),
    path("<uuid:website_id>/<uuid:lead_id>/email/", views.LeadEmailView.as_view(), name="lead-email"),
]
