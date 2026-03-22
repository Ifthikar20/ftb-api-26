from django.urls import path

from . import tracking_views

urlpatterns = [
    path("", tracking_views.TrackedLinkRedirectView.as_view(), name="tracked-link-redirect"),
]
