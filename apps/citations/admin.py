from django.contrib import admin

from apps.citations.models import (
    Citation,
    DomainClassification,
    SourceInfluenceSnapshot,
)


@admin.register(Citation)
class CitationAdmin(admin.ModelAdmin):
    list_display = ("apex_domain", "source_class", "extraction_method", "confidence", "audit_id")
    list_filter = ("source_class", "extraction_method")
    search_fields = ("apex_domain", "url", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DomainClassification)
class DomainClassificationAdmin(admin.ModelAdmin):
    list_display = ("apex_domain", "source_class", "classified_by", "updated_at")
    list_filter = ("source_class", "classified_by")
    search_fields = ("apex_domain",)


@admin.register(SourceInfluenceSnapshot)
class SourceInfluenceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("provider", "website", "industry", "period_start", "period_end", "total_citations")
    list_filter = ("provider",)
