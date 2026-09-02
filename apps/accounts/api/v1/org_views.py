"""Organization management API (mounted at /api/v1/orgs/).

Single-org model: every authenticated route resolves THE requester's org
through the permission classes (`request.org_membership`) — no org id in
the URL, so there is nothing to tamper with. The invitation preview/
accept/register routes are token-addressed and public by design.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.org_serializers import (
    InvitationSerializer,
    OrganizationMemberSerializer,
    OrganizationSerializer,
    OrgDomainSerializer,
)
from apps.accounts.api.v1.views import _refresh_cookie_settings
from apps.accounts.models import User
from apps.accounts.services.org_service import OrgService
from core.interceptors.throttling import AuthRateThrottle
from core.permissions.org import (
    IsOrgAdmin,
    IsOrgMember,
    IsOrgOwner,
    OrgFeaturesGate,
)


class CurrentOrgView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        membership = request.org_membership
        org = membership.organization
        org.member_count = org.members.count()
        return Response(
            OrganizationSerializer(org, context={"membership": membership}).data
        )

    def patch(self, request):
        from core.exceptions import PermissionDenied
        from core.permissions.rbac import role_at_least

        membership = request.org_membership
        if not role_at_least(membership.role, "admin"):
            raise PermissionDenied("This action requires an organization admin.")
        org = membership.organization
        serializer = OrganizationSerializer(
            org, data=request.data, partial=True, context={"membership": membership}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        org.member_count = org.members.count()
        return Response(
            OrganizationSerializer(org, context={"membership": membership}).data
        )


class OrgMembersView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        membership = request.org_membership
        members = (
            membership.organization.members.select_related("user")
            .order_by("created_at")
        )
        return Response(
            OrganizationMemberSerializer(
                members, many=True, context={"membership": membership}
            ).data
        )


class OrgMemberDetailView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def patch(self, request, member_id: int):
        role = request.data.get("role", "")
        member = OrgService.change_role(
            acting=request.org_membership, member_id=member_id, role=role
        )
        return Response(
            OrganizationMemberSerializer(
                member, context={"membership": request.org_membership}
            ).data
        )

    def delete(self, request, member_id: int):
        OrgService.remove_member(
            acting=request.org_membership, member_id=member_id
        )
        return Response({"ok": True})


class OrgInvitationsView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get(self, request):
        from django.utils import timezone

        pending = request.org_membership.organization.invitations.filter(
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).select_related("invited_by").order_by("-created_at")
        return Response(InvitationSerializer(pending, many=True).data)

    def post(self, request):
        invitation = OrgService.create_invitation(
            acting=request.org_membership,
            email=request.data.get("email", ""),
            role=request.data.get("role", "member"),
        )
        return Response(
            InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class OrgInvitationDetailView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def delete(self, request, invitation_id):
        OrgService.revoke_invitation(
            acting=request.org_membership, invitation_id=invitation_id
        )
        return Response({"ok": True})


class OrgInvitationResendView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def post(self, request, invitation_id):
        invitation = OrgService.resend_invitation(
            acting=request.org_membership, invitation_id=invitation_id
        )
        return Response({"ok": True, "expires_at": invitation.expires_at})


class InvitationPreviewView(OrgFeaturesGate, APIView):
    """Public, token-addressed. Powers the /invite/<token> landing page.

    Rate-limited and hash-compared; an invalid token 404s with no detail,
    so this can't be used to enumerate anything.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def get(self, request, token: str):
        invitation = OrgService.invitation_by_token(token)
        org = invitation.organization
        return Response({
            "org": {"name": org.name, "logo_url": org.logo_url},
            "email": invitation.email,
            "role": invitation.role,
            "invited_by_name": (
                invitation.invited_by.full_name if invitation.invited_by else ""
            ),
            "expires_at": invitation.expires_at,
            "user_exists": User.objects.filter(
                email__iexact=invitation.email
            ).exists(),
            "sso_enforced": org.require_sso,
        })


class InvitationAcceptView(OrgFeaturesGate, APIView):
    """An existing, signed-in account accepts its invitation."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, token: str):
        member = OrgService.accept_invitation_existing(
            raw_token=token, user=request.user
        )
        return Response({
            "org": {
                "id": str(member.organization_id),
                "name": member.organization.name,
            },
            "role": member.role,
        })


class InvitationRegisterView(OrgFeaturesGate, APIView):
    """A brand-new account is created from its invitation and logged in.

    The response is login-shaped and sets the refresh cookie — the SPA
    treats it exactly like POST /auth/login/.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, token: str):
        result = OrgService.register_via_invitation(
            raw_token=token,
            full_name=request.data.get("full_name", "").strip(),
            password=request.data.get("password", ""),
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        response = Response(
            {"access": result["access"], "user": result["user"], "org": result["org"]},
            status=status.HTTP_201_CREATED,
        )
        response.set_cookie(value=result["refresh"], **_refresh_cookie_settings())
        return response


class OrgDomainsView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get(self, request):
        domains = request.org_membership.organization.domains.order_by("created_at")
        return Response(OrgDomainSerializer(domains, many=True).data)

    def post(self, request):
        from apps.accounts.services.domain_service import DomainService

        domain = DomainService.claim(
            acting=request.org_membership, domain=request.data.get("domain", "")
        )
        return Response(
            OrgDomainSerializer(domain).data, status=status.HTTP_201_CREATED
        )


class OrgDomainDetailView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def patch(self, request, domain_id):
        from apps.accounts.services.domain_service import DomainService

        domain = None
        if "auto_join" in request.data:
            domain = DomainService.set_auto_join(
                acting=request.org_membership,
                domain_id=domain_id,
                enabled=bool(request.data["auto_join"]),
            )
        if "entra_tenant_id" in request.data:
            domain = DomainService.set_entra_tenant(
                acting=request.org_membership,
                domain_id=domain_id,
                tenant_id=str(request.data["entra_tenant_id"] or ""),
            )
        if domain is not None:
            return Response(OrgDomainSerializer(domain).data)
        return Response(
            {"error": {"code": "validation_error", "message": "Nothing to update."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, domain_id):
        from apps.accounts.services.domain_service import DomainService

        DomainService.remove(acting=request.org_membership, domain_id=domain_id)
        return Response({"ok": True})


class OrgDomainVerifyView(OrgFeaturesGate, APIView):
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def post(self, request, domain_id):
        from apps.accounts.services.domain_service import DomainService

        domain, verified = DomainService.verify(
            acting=request.org_membership, domain_id=domain_id
        )
        payload = OrgDomainSerializer(domain).data
        payload["status"] = "verified" if verified else "pending_dns"
        return Response(payload)


class OrgUsageView(OrgFeaturesGate, APIView):
    """Seat and usage rollup for the current calendar month (admin+).

    This is the dataset custom enterprise pricing is negotiated against:
    seats occupied vs sold, each member's dedicated-prompt draw-down, and
    the org's actual AI cost. Read-only.
    """

    permission_classes = [IsAuthenticated, IsOrgAdmin]

    def get(self, request):
        from django.db.models import Sum
        from django.utils import timezone

        from apps.accounts.models import AITokenUsage
        from apps.billing.services.org_entitlements import (
            monthly_prompt_allowance_for,
            prompts_used_this_month,
            seat_limit_for,
            seats_used,
        )

        org = request.org_membership.organization
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        members = list(org.members.select_related("user").order_by("created_at"))
        member_users = [m.user for m in members]

        cost_by_user = dict(
            AITokenUsage.objects.filter(
                user__in=member_users, created_at__gte=month_start,
            )
            .values_list("user_id")
            .annotate(total=Sum("estimated_cost_usd"))
        )

        rows = []
        total_prompts = 0
        for m in members:
            used = prompts_used_this_month(m.user)
            total_prompts += used
            rows.append({
                "user": {
                    "id": str(m.user.id),
                    "full_name": m.user.full_name,
                    "email": m.user.email,
                },
                "role": m.role,
                "prompts_used": used,
                "prompt_allowance": monthly_prompt_allowance_for(m.user),
                "ai_cost_usd": float(cost_by_user.get(m.user.id) or 0),
                "last_login": m.user.last_login,
            })

        seat_cap = seat_limit_for(org)
        return Response({
            "period": {"start": month_start, "end": now},
            "seats": {
                "used": seats_used(org),
                "max": seat_cap if seat_cap > 0 else -1,
            },
            "members": rows,
            "totals": {
                "prompts_used": total_prompts,
                "ai_cost_usd": round(
                    sum(r["ai_cost_usd"] for r in rows), 4
                ),
                "members": len(rows),
            },
        })


class OrgSsoEnforceView(OrgFeaturesGate, APIView):
    """Owner-only: require (or stop requiring) SSO for every member."""

    permission_classes = [IsAuthenticated, IsOrgOwner]

    def post(self, request):
        enabled = bool(request.data.get("enabled", True))
        acting_jti = None
        # Keep the acting owner's session alive through the revocation
        # sweep: their refresh cookie's jti is excluded from the blacklist.
        refresh_cookie = request.COOKIES.get("refresh_token")
        if refresh_cookie:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                acting_jti = RefreshToken(refresh_cookie)["jti"]
            except Exception:
                acting_jti = None

        revoked = OrgService.set_sso_enforcement(
            acting=request.org_membership, enabled=enabled, acting_jti=acting_jti
        )
        return Response({"require_sso": enabled, "sessions_revoked": revoked})
