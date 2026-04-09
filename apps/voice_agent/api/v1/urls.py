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

    # Phone numbers
    path("<uuid:website_id>/phone-numbers/", views.PhoneNumberListView.as_view(), name="voice-phone-list"),
    path("<uuid:website_id>/phone-numbers/<uuid:number_id>/", views.PhoneNumberDetailView.as_view(), name="voice-phone-detail"),

    # Agent context documents (knowledge base)
    path("<uuid:website_id>/context-docs/", views.AgentContextDocumentListView.as_view(), name="voice-context-list"),
    path("<uuid:website_id>/context-docs/upload/", views.AgentContextDocumentUploadView.as_view(), name="voice-context-upload"),
    path("<uuid:website_id>/context-docs/<uuid:doc_id>/", views.AgentContextDocumentDetailView.as_view(), name="voice-context-detail"),

    # Retell AI webhook (no website_id — determined from agent_id in payload)
    path("webhook/retell/", views.RetellWebhookView.as_view(), name="voice-retell-webhook"),
]
