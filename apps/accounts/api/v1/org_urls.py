from django.urls import path

from apps.accounts.api.v1 import org_views

urlpatterns = [
    path("current/", org_views.CurrentOrgView.as_view(), name="org-current"),
    path("current/members/", org_views.OrgMembersView.as_view(), name="org-members"),
    path(
        "current/members/<int:member_id>/",
        org_views.OrgMemberDetailView.as_view(),
        name="org-member-detail",
    ),
    path(
        "current/invitations/",
        org_views.OrgInvitationsView.as_view(),
        name="org-invitations",
    ),
    path(
        "current/invitations/<uuid:invitation_id>/",
        org_views.OrgInvitationDetailView.as_view(),
        name="org-invitation-detail",
    ),
    path(
        "current/invitations/<uuid:invitation_id>/resend/",
        org_views.OrgInvitationResendView.as_view(),
        name="org-invitation-resend",
    ),
    path("current/domains/", org_views.OrgDomainsView.as_view(), name="org-domains"),
    path(
        "current/domains/<uuid:domain_id>/",
        org_views.OrgDomainDetailView.as_view(),
        name="org-domain-detail",
    ),
    path(
        "current/domains/<uuid:domain_id>/verify/",
        org_views.OrgDomainVerifyView.as_view(),
        name="org-domain-verify",
    ),
    path(
        "current/sso/enforce/",
        org_views.OrgSsoEnforceView.as_view(),
        name="org-sso-enforce",
    ),
    path("current/usage/", org_views.OrgUsageView.as_view(), name="org-usage"),
    # Token-addressed invitation flow (public preview/register; accept
    # requires the invited account to be signed in).
    path(
        "invitations/<str:token>/",
        org_views.InvitationPreviewView.as_view(),
        name="invitation-preview",
    ),
    path(
        "invitations/<str:token>/accept/",
        org_views.InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
    path(
        "invitations/<str:token>/register/",
        org_views.InvitationRegisterView.as_view(),
        name="invitation-register",
    ),
]
