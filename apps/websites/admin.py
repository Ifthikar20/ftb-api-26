from django.contrib import admin
from apps.websites.models import Website, WebsiteMembership, Integration


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "user", "pixel_verified", "created_at")
    list_filter = ("pixel_verified", "is_active")
    search_fields = ("name", "url", "user__email")
    readonly_fields = ("id", "pixel_key", "created_at", "updated_at")


@admin.register(WebsiteMembership)
class WebsiteMembershipAdmin(admin.ModelAdmin):
    list_display = ("website", "user", "role", "accepted")


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("website", "type", "is_active", "connected_at")
