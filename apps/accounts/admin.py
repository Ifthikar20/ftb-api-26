from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User, UserProfile, LoginAttempt


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "plan", "is_email_verified", "is_active", "created_at")
    list_filter = ("plan", "is_email_verified", "is_active", "is_staff")
    search_fields = ("email", "full_name", "company_name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal", {"fields": ("full_name", "company_name")}),
        ("Plan", {"fields": ("plan",)}),
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
