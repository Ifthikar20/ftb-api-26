"""URL routes for the claim_verifier REST API."""
from django.urls import path

from . import views

urlpatterns = [
    path(
        "websites/<uuid:website_id>/mismatches/",
        views.WebsiteMismatchesView.as_view(),
        name="claim-verifier-website-mismatches",
    ),
    path(
        "websites/<uuid:website_id>/accuracy/",
        views.WebsiteAccuracyView.as_view(),
        name="claim-verifier-website-accuracy",
    ),
    path(
        "audits/<uuid:audit_id>/claims/",
        views.AuditClaimsView.as_view(),
        name="claim-verifier-audit-claims",
    ),
    path(
        "claims/<uuid:claim_id>/",
        views.ClaimDetailView.as_view(),
        name="claim-verifier-claim-detail",
    ),
    path(
        "mismatches/<uuid:mismatch_id>/dismiss/",
        views.MismatchDismissView.as_view(),
        name="claim-verifier-mismatch-dismiss",
    ),
]
