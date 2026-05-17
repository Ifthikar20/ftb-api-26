from django.contrib import admin

from apps.content_studio.models import ContentBrief, ContentDraft


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
