from django.urls import path
from . import views

urlpatterns = [
    path("event/", views.EventIngestView.as_view(), name="pixel-event"),
    path("batch/", views.BatchEventIngestView.as_view(), name="pixel-batch"),
]
