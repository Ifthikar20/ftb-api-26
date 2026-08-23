from django.urls import path

from apps.assistant.api.v1 import views

urlpatterns = [
    path("status/", views.AssistantStatusView.as_view(), name="assistant-status"),
    path(
        "<uuid:website_id>/ask/",
        views.AssistantAskView.as_view(),
        name="assistant-ask",
    ),
]
