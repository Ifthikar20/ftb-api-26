from django.contrib import admin

from apps.content_studio.models import (
    ContentBrief,
    ContentDraft,
    PublishLog,
    PublishTarget,
    ROIAttribution,
)


@admin.register(ContentBrief)
class ContentBriefAdmin(admin.ModelAdmin):
    list_display = ("headline", "gap_type", "target_format", "impact_score", "status", "website")
    list_filter = ("gap_type", "target_format", "status")
    search_fields = ("headline", "description")
    readonly_fields = ("created_at", "updated_at", "dedupe_key")


@admin.register(ContentDraft)
class ContentDraftAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "revision", "voice_score", "accuracy_score", "website")
    list_filter = ("status", "generated_by")
    search_fields = ("title", "body_markdown")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PublishTarget)
class PublishTargetAdmin(admin.ModelAdmin):
    list_display = ("provider", "label", "is_active", "is_default", "website")
    list_filter = ("provider", "is_active")


@admin.register(PublishLog)
class PublishLogAdmin(admin.ModelAdmin):
    list_display = ("draft", "target", "status", "external_id", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ROIAttribution)
class ROIAttributionAdmin(admin.ModelAdmin):
    list_display = ("draft", "measured_at", "visibility_lift", "citation_count_after")
    readonly_fields = ("created_at", "updated_at")
