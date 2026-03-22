from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:website_id>/generate/", views.GenerateStrategyView.as_view(), name="strategy-generate"),
    path("<uuid:website_id>/current/", views.CurrentStrategyView.as_view(), name="strategy-current"),
    path("<uuid:website_id>/history/", views.StrategyHistoryView.as_view(), name="strategy-history"),
    path("<uuid:website_id>/actions/", views.ActionsView.as_view(), name="strategy-actions"),
    path("<uuid:website_id>/actions/<uuid:action_id>/", views.ActionDetailView.as_view(), name="strategy-action-detail"),
    path("<uuid:website_id>/calendar/", views.CalendarView.as_view(), name="strategy-calendar"),
    path("<uuid:website_id>/chat/", views.ChatView.as_view(), name="strategy-chat"),
    path("<uuid:website_id>/chat/history/", views.ChatHistoryView.as_view(), name="strategy-chat-history"),
    path("<uuid:website_id>/brief/", views.MorningBriefView.as_view(), name="strategy-brief"),
    path("<uuid:website_id>/predictions/", views.PredictionsView.as_view(), name="strategy-predictions"),
]
