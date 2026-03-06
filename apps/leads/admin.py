from django.contrib import admin
from apps.leads.models import Lead, LeadNote, ScoringConfig


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "website", "score", "status", "email", "company", "created_at")
    list_filter = ("status",)
    search_fields = ("email", "company", "name")
    ordering = ("-score",)


@admin.register(ScoringConfig)
class ScoringConfigAdmin(admin.ModelAdmin):
    list_display = ("website", "threshold")
