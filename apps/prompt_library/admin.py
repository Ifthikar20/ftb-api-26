from django.contrib import admin

from apps.prompt_library.models import (
    Industry,
    Prompt,
    PromptSampleEntry,
    PromptSampleRun,
    PromptVariation,
)


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ("text_short", "industry", "intent_bucket", "source", "demand_score", "is_active")
    list_filter = ("intent_bucket", "source", "is_active", "industry")
    search_fields = ("text",)
    raw_id_fields = ("industry",)

    @admin.display(description="Text")
    def text_short(self, obj):
        return obj.text[:80]


@admin.register(PromptVariation)
class PromptVariationAdmin(admin.ModelAdmin):
    list_display = ("parent_prompt", "created_at")
    raw_id_fields = ("parent_prompt",)


class PromptSampleEntryInline(admin.TabularInline):
    model = PromptSampleEntry
    extra = 0
    raw_id_fields = ("prompt",)


@admin.register(PromptSampleRun)
class PromptSampleRunAdmin(admin.ModelAdmin):
    list_display = ("audit_run", "industry", "strategy", "seed", "created_at")
    raw_id_fields = ("audit_run", "industry")
    inlines = [PromptSampleEntryInline]
