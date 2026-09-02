from rest_framework import serializers

from apps.accounts.models import Invitation, Organization, OrganizationMember, OrgDomain
from core.permissions.rbac import role_at_least
from core.utils.constants import OrgRole


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "logo_url", "plan", "require_sso",
            "member_count", "my_role", "created_at",
        ]
        read_only_fields = ["id", "slug", "plan", "require_sso", "created_at"]

    def get_my_role(self, obj) -> str:
        membership = self.context.get("membership")
        return membership.role if membership else ""


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMember
        fields = ["id", "user", "role", "joined_via", "can_manage", "created_at"]

    def get_user(self, obj) -> dict:
        return {
            "id": str(obj.user.id),
            "full_name": obj.user.full_name,
            "email": obj.user.email,
        }

    def get_can_manage(self, obj) -> bool:
        """Whether the ACTING user may edit/remove this row.

        Computed server-side so the SPA never re-implements the role
        ladder: owner rows and your own row are immutable; admins need
        owner privileges to be touched; otherwise admin+ suffices.
        """
        acting = self.context.get("membership")
        if acting is None:
            return False
        if obj.role == OrgRole.OWNER or obj.user_id == acting.user_id:
            return False
        required = OrgRole.OWNER if obj.role == OrgRole.ADMIN else OrgRole.ADMIN
        return role_at_least(acting.role, required)


class InvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ["id", "email", "role", "invited_by", "created_at", "expires_at"]

    def get_invited_by(self, obj) -> dict | None:
        if not obj.invited_by:
            return None
        return {"id": str(obj.invited_by.id), "full_name": obj.invited_by.full_name}


class OrgDomainSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    txt_host = serializers.SerializerMethodField()
    txt_record = serializers.SerializerMethodField()

    class Meta:
        model = OrgDomain
        fields = [
            "id", "domain", "method", "status", "txt_host", "txt_record",
            "verified_at", "auto_join", "entra_tenant_id", "last_checked_at",
        ]
        read_only_fields = [
            "id", "method", "verified_at", "last_checked_at",
        ]

    def get_status(self, obj) -> str:
        if obj.verified_at:
            return "verified"
        return "failed" if obj.consecutive_failures else "pending_dns"

    def get_txt_host(self, obj) -> str:
        return f"_cansee.{obj.domain}"

    def get_txt_record(self, obj) -> str:
        return f"cansee-verification={obj.dns_token}"
