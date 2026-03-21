from django.contrib import admin
from apps.leads.models import Lead, LeadNote, LeadSegment, ScoringConfig


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "website", "score", "status", "email", "company", "created_at")
    list_filter = ("status",)
    search_fields = ("email", "company", "name")
    ordering = ("-score",)


@admin.register(LeadNote)
class LeadNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "author", "created_at")
    search_fields = ("content",)
    ordering = ("-created_at",)


@admin.register(LeadSegment)
class LeadSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "website", "created_by", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(ScoringConfig)
class ScoringConfigAdmin(admin.ModelAdmin):
    list_display = ("website", "threshold")
