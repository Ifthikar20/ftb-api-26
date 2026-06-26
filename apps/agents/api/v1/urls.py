"""URL routes for the agents REST API (mounted at /api/v1/agents/)."""
from django.urls import path

from . import views

urlpatterns = [
    path("catalog/", views.AgentCatalogView.as_view(), name="agents-catalog"),
    path("hire/", views.HireAgentView.as_view(), name="agents-hire"),
    path("hired/", views.HiredAgentListView.as_view(), name="agents-hired-list"),
    path("hired/<uuid:hired_id>/", views.HiredAgentDetailView.as_view(), name="agents-hired-detail"),
    path("hired/<uuid:hired_id>/run/", views.HiredAgentRunNowView.as_view(), name="agents-hired-run"),
    path("hired/<uuid:hired_id>/insights/", views.AgentInsightsView.as_view(), name="agents-hired-insights"),
    path("hired/<uuid:hired_id>/chat/", views.AgentChatView.as_view(), name="agents-hired-chat"),
    path("hired/<uuid:hired_id>/actions/", views.AgentActionsView.as_view(), name="agents-hired-actions"),
    path("actions/<uuid:action_id>/<str:decision>/", views.AgentActionDecisionView.as_view(), name="agents-action-decision"),
]
