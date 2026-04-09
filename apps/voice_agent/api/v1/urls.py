from django.urls import path

from . import views

urlpatterns = [
    # Agent configuration
    path("<uuid:website_id>/config/", views.AgentConfigView.as_view(), name="voice-agent-config"),
    path("<uuid:website_id>/activate/", views.AgentActivateView.as_view(), name="voice-agent-activate"),
    path("<uuid:website_id>/web-call/", views.WebCallView.as_view(), name="voice-agent-web-call"),

    # Call logs
    path("<uuid:website_id>/calls/", views.CallLogListView.as_view(), name="voice-call-list"),
    path("<uuid:website_id>/calls/stats/", views.CallStatsView.as_view(), name="voice-call-stats"),
    path("<uuid:website_id>/calls/<uuid:call_id>/", views.CallLogDetailView.as_view(), name="voice-call-detail"),

    # Calendar / Appointments
    path("<uuid:website_id>/calendar/", views.CalendarEventListView.as_view(), name="voice-calendar-list"),
    path("<uuid:website_id>/calendar/availability/", views.AvailabilityView.as_view(), name="voice-calendar-availability"),
    path("<uuid:website_id>/calendar/<uuid:event_id>/", views.CalendarEventDetailView.as_view(), name="voice-calendar-detail"),

    # Callback reminders
    path("<uuid:website_id>/reminders/", views.CallbackReminderListView.as_view(), name="voice-reminder-list"),
    path("<uuid:website_id>/reminders/<uuid:reminder_id>/", views.CallbackReminderDetailView.as_view(), name="voice-reminder-detail"),

    # Todos / Action items (AI-extracted from calls)
    path("<uuid:website_id>/todos/", views.TodoListView.as_view(), name="voice-todo-list"),
    path("<uuid:website_id>/todos/stats/", views.TodoStatsView.as_view(), name="voice-todo-stats"),
    path("<uuid:website_id>/todos/<uuid:todo_id>/", views.TodoDetailView.as_view(), name="voice-todo-detail"),

    # Call extraction (AI analysis results)
    path("<uuid:website_id>/calls/<uuid:call_id>/extraction/", views.CallExtractionView.as_view(), name="voice-call-extraction"),

    # Lead detection: calls flagged as possible leads from their transcript
    path("<uuid:website_id>/lead-detection/", views.PossibleLeadListView.as_view(), name="voice-lead-detection-list"),
    path("<uuid:website_id>/lead-detection/<uuid:call_id>/", views.PossibleLeadActionView.as_view(), name="voice-lead-detection-action"),

    # Usage / billing dashboard
    path("<uuid:website_id>/usage/", views.VoiceUsageView.as_view(), name="voice-usage"),

    # Phone numbers
    path("<uuid:website_id>/phone-numbers/", views.PhoneNumberListView.as_view(), name="voice-phone-list"),
    path("<uuid:website_id>/phone-numbers/verify/start/", views.PhoneNumberVerifyStartView.as_view(), name="voice-phone-verify-start"),
    path("<uuid:website_id>/phone-numbers/verify/confirm/", views.PhoneNumberVerifyConfirmView.as_view(), name="voice-phone-verify-confirm"),
    path("<uuid:website_id>/phone-numbers/<uuid:number_id>/", views.PhoneNumberDetailView.as_view(), name="voice-phone-detail"),

    # Agent context documents (knowledge base)
    path("<uuid:website_id>/context-docs/", views.AgentContextDocumentListView.as_view(), name="voice-context-list"),
    path("<uuid:website_id>/context-docs/upload/", views.AgentContextDocumentUploadView.as_view(), name="voice-context-upload"),
    path("<uuid:website_id>/context-docs/<uuid:doc_id>/", views.AgentContextDocumentDetailView.as_view(), name="voice-context-detail"),

    # Retell AI webhook (no website_id — determined from agent_id in payload)
    path("webhook/retell/", views.RetellWebhookView.as_view(), name="voice-retell-webhook"),

    # Outbound calling: campaigns + targets + call-now
    path("<uuid:website_id>/campaigns/", views.CallCampaignListView.as_view(), name="voice-campaign-list"),
    path("<uuid:website_id>/campaigns/<uuid:campaign_id>/", views.CallCampaignDetailView.as_view(), name="voice-campaign-detail"),
    path("<uuid:website_id>/campaigns/<uuid:campaign_id>/targets/", views.CallTargetListView.as_view(), name="voice-campaign-targets"),
    path("<uuid:website_id>/campaigns/<uuid:campaign_id>/targets/upload/", views.CallTargetCSVUploadView.as_view(), name="voice-campaign-targets-upload"),
    path("<uuid:website_id>/campaigns/<uuid:campaign_id>/start/", views.CampaignStartView.as_view(), name="voice-campaign-start"),
    path("<uuid:website_id>/campaigns/<uuid:campaign_id>/pause/", views.CampaignPauseView.as_view(), name="voice-campaign-pause"),
    path("<uuid:website_id>/call-now/", views.CallNowView.as_view(), name="voice-call-now"),

    # Internal endpoints used by the LiveKit agent worker (bearer-token auth)
    path("internal/agent-bootstrap/", views.InternalAgentBootstrapView.as_view(), name="voice-internal-bootstrap"),
    path("internal/calls/finish/", views.InternalCallFinishView.as_view(), name="voice-internal-call-finish"),

    # Onboarding: starter templates + setup checklist
    path("onboarding/templates/", views.OnboardingTemplateListView.as_view(), name="voice-onboarding-templates"),
    path("<uuid:website_id>/onboarding/setup-status/", views.OnboardingSetupStatusView.as_view(), name="voice-onboarding-status"),
    path("<uuid:website_id>/onboarding/templates/<slug:slug>/preview/", views.OnboardingTemplatePreviewView.as_view(), name="voice-onboarding-template-preview"),
    path("<uuid:website_id>/onboarding/templates/<slug:slug>/apply/", views.OnboardingTemplateApplyView.as_view(), name="voice-onboarding-template-apply"),
]
