from django.urls import path
from .api.v1 import views

app_name = "gamification"

urlpatterns = [
    path("api/v1/gamification/progress/", views.progress_view, name="progress"),
    path("api/v1/gamification/cards/", views.cards_view, name="cards"),
    path("api/v1/gamification/status/", views.feature_status_view, name="status"),
]
