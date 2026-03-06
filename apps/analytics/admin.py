from django.contrib import admin
from apps.analytics.models import Visitor, PageEvent, Session


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
