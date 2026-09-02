from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import (
    Invitation,
    LoginAttempt,
    Organization,
    OrganizationMember,
    OrgDomain,
    SocialIdentity,
    User,
    UserProfile,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "plan", "is_email_verified", "is_active", "created_at")
    list_filter = (
        "plan", "is_email_verified", "is_active", "is_staff",
        ("paywall_dismissed_at", admin.EmptyFieldListFilter),
    )
    search_fields = ("email", "full_name", "company_name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal", {"fields": ("full_name", "company_name")}),
        ("Plan", {"fields": ("plan", "paywall_dismissed_at")}),
        ("Status", {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified", "onboarding_complete")}),
        ("Dates", {"fields": ("last_login", "last_daily_brief", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2"),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone")
    search_fields = ("user__email",)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("email", "ip_address", "success", "timestamp")
    list_filter = ("success",)
    search_fields = ("email", "ip_address")
    readonly_fields = ("email", "ip_address", "user_agent", "success", "user", "timestamp")


class OrganizationMemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 0
    autocomplete_fields = ("user", "invited_by")


class OrgDomainInline(admin.TabularInline):
    model = OrgDomain
    extra = 0
    readonly_fields = ("dns_token", "verified_at", "last_checked_at", "consecutive_failures")
    fields = (
        "domain", "method", "auto_join", "entra_tenant_id",
        "dns_token", "verified_at", "last_checked_at", "consecutive_failures",
    )


class InvitationInline(admin.TabularInline):
    model = Invitation
    extra = 0
    readonly_fields = ("token_hash", "accepted_at", "revoked_at")
    fields = ("email", "role", "invited_by", "expires_at", "token_hash", "accepted_at", "revoked_at")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name", "slug", "plan", "seat_limit", "monthly_prompt_allowance",
        "require_sso", "member_count", "created_at",
    )
    search_fields = ("name", "slug", "owner__email")
    list_filter = ("plan", "require_sso")
    autocomplete_fields = ("owner",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [OrganizationMemberInline, OrgDomainInline, InvitationInline]

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.members.count()


@admin.register(SocialIdentity)
class SocialIdentityAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "subject", "tenant", "last_login_at")
    search_fields = ("user__email", "subject", "tenant")
    readonly_fields = ("user", "provider", "subject", "tenant", "email_at_link", "last_login_at")
