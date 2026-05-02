from django.urls import path

from apps.onboarding.api.v1 import views

urlpatterns = [
    path("scan/", views.OnboardingScanView.as_view(), name="onboarding-scan"),
    path("save/", views.OnboardingSaveView.as_view(), name="onboarding-save"),
]
