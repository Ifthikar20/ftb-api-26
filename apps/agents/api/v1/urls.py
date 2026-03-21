from django.urls import path
from . import views

urlpatterns = [
    path("types/", views.AgentTypesView.as_view(), name="agent-types"),
    path("activity/", views.AgentActivityView.as_view(), name="agent-activity"),
    path("<uuid:website_id>/runs/", views.AgentRunsView.as_view(), name="agent-runs"),
    path("<uuid:website_id>/runs/<uuid:run_id>/", views.AgentRunDetailView.as_view(), name="agent-run-detail"),
    path("<uuid:website_id>/runs/<uuid:run_id>/approve/", views.AgentRunApproveView.as_view(), name="agent-run-approve"),
    path("<uuid:website_id>/runs/<uuid:run_id>/cancel/", views.AgentRunCancelView.as_view(), name="agent-run-cancel"),
]
