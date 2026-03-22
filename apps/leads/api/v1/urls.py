from django.urls import path

from . import views

urlpatterns = [
    # Leads
    path("<uuid:website_id>/", views.LeadListView.as_view(), name="lead-list"),
    path("<uuid:website_id>/hot/", views.HotLeadsView.as_view(), name="lead-hot"),
    path("<uuid:website_id>/export/", views.LeadExportView.as_view(), name="lead-export"),
    path("<uuid:website_id>/export-xlsx/", views.LeadExportXlsxView.as_view(), name="lead-export-xlsx"),
    path("<uuid:website_id>/export-drive/", views.LeadExportDriveView.as_view(), name="lead-export-drive"),
    path("<uuid:website_id>/scoring-config/", views.ScoringConfigView.as_view(), name="lead-scoring-config"),
    path("<uuid:website_id>/segments/", views.LeadSegmentListView.as_view(), name="lead-segment-list"),
    path("<uuid:website_id>/segments/<uuid:segment_id>/", views.LeadSegmentDetailView.as_view(), name="lead-segment-detail"),
    path("<uuid:website_id>/<uuid:lead_id>/", views.LeadDetailView.as_view(), name="lead-detail"),
    path("<uuid:website_id>/<uuid:lead_id>/note/", views.LeadNoteView.as_view(), name="lead-note"),
    path("<uuid:website_id>/ai-search/", views.AILeadFinderView.as_view(), name="lead-ai-search"),
    path("<uuid:website_id>/<uuid:lead_id>/email/", views.LeadEmailView.as_view(), name="lead-email"),
    # Campaigns
    path("<uuid:website_id>/campaigns/", views.CampaignListView.as_view(), name="campaign-list"),
    path("<uuid:website_id>/campaigns/<int:campaign_id>/", views.CampaignDetailView.as_view(), name="campaign-detail"),
    path("<uuid:website_id>/campaigns/<int:campaign_id>/send/", views.CampaignSendView.as_view(), name="campaign-send"),
    path("<uuid:website_id>/campaigns/<int:campaign_id>/stats/", views.CampaignStatsView.as_view(), name="campaign-stats"),
    path("<uuid:website_id>/campaigns/<int:campaign_id>/recipients/", views.CampaignRecipientsView.as_view(), name="campaign-recipients"),
    # Tracked links
    path("<uuid:website_id>/tracked-links/", views.TrackedLinkListView.as_view(), name="tracked-link-list"),
    path("<uuid:website_id>/tracked-links/<uuid:link_id>/", views.TrackedLinkDetailView.as_view(), name="tracked-link-detail"),
    path("<uuid:website_id>/tracked-links/<uuid:link_id>/clicks/", views.TrackedLinkClicksView.as_view(), name="tracked-link-clicks"),
]
