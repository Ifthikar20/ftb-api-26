from django.urls import path

from apps.assistant.api.v1 import views

urlpatterns = [
    path("status/", views.AssistantStatusView.as_view(), name="assistant-status"),
    path(
        "<uuid:website_id>/ask/",
        views.AssistantAskView.as_view(),
        name="assistant-ask",
    ),
    path(
        "<uuid:website_id>/conversations/",
        views.AssistantConversationListView.as_view(),
        name="assistant-conversations",
    ),
    path(
        "<uuid:website_id>/conversations/<uuid:conversation_id>/",
        views.AssistantConversationDetailView.as_view(),
        name="assistant-conversation-detail",
    ),
]
