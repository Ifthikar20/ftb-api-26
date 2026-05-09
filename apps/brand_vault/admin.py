from django.contrib import admin

from apps.brand_vault.models import BrandFact, FactRevision


@admin.register(BrandFact)
class BrandFactAdmin(admin.ModelAdmin):
    list_display = ("subject", "predicate", "status", "confidence", "website", "version_to")
    list_filter = ("status", "extracted_by", "product_line")
    search_fields = ("subject", "predicate", "object", "source_url")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FactRevision)
class FactRevisionAdmin(admin.ModelAdmin):
    list_display = ("fact", "action", "actor_user", "created_at")
    list_filter = ("action",)
