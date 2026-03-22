from django.contrib import admin

from apps.analytics.models import LinkClick, PageEvent, TrackedLink, Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("fingerprint_hash", "website", "geo_country", "lead_score", "visit_count", "last_seen")
    list_filter = ("geo_country", "device_type")
    search_fields = ("fingerprint_hash", "company_name")
    readonly_fields = ("id", "fingerprint_hash", "first_seen", "last_seen")


@admin.register(PageEvent)
class PageEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "url", "visitor", "timestamp")
    list_filter = ("event_type",)
    readonly_fields = ("id", "timestamp")


@admin.register(TrackedLink)
class TrackedLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "website", "tracking_key", "destination_url", "click_count", "conversion_count", "created_at")
    search_fields = ("tracking_key", "destination_url", "website__name")
    readonly_fields = ("id", "tracking_key", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(LinkClick)
class LinkClickAdmin(admin.ModelAdmin):
    list_display = ("id", "tracked_link", "ip_address", "converted", "clicked_at")
    list_filter = ("converted",)
    readonly_fields = ("id", "clicked_at")
