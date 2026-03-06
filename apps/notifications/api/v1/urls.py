from django.urls import path
from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("unread/", views.UnreadNotificationsView.as_view(), name="notification-unread"),
    path("read-all/", views.ReadAllNotificationsView.as_view(), name="notification-read-all"),
    path("preferences/", views.NotificationPreferencesView.as_view(), name="notification-preferences"),
    path("<uuid:pk>/read/", views.NotificationReadView.as_view(), name="notification-read"),
    path("<uuid:pk>/", views.NotificationDetailView.as_view(), name="notification-detail"),
]
