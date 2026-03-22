from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:website_id>/run/", views.AuditRunView.as_view(), name="audit-run"),
    path("<uuid:website_id>/status/", views.AuditStatusView.as_view(), name="audit-status"),
    path("<uuid:website_id>/latest/", views.AuditLatestView.as_view(), name="audit-latest"),
    path("<uuid:website_id>/history/", views.AuditHistoryView.as_view(), name="audit-history"),
    path("<uuid:website_id>/<uuid:audit_id>/", views.AuditDetailView.as_view(), name="audit-detail"),
    path("<uuid:website_id>/grader/", views.SEOGraderView.as_view(), name="seo-grader"),
    path("<uuid:website_id>/grader/<int:issue_id>/deploy/", views.SEOGraderDeployView.as_view(), name="seo-grader-deploy"),
]
