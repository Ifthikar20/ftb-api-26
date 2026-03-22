from django.contrib import admin
from apps.leads.models import Lead, LeadNote, LeadSegment, ScoringConfig, EmailCampaign, CampaignRecipient


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


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "website", "status", "sent_count", "open_rate", "click_rate", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "subject", "website__name")
    readonly_fields = ("id", "created_at", "updated_at", "sent_at")
    ordering = ("-created_at",)


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "lead", "sent_at", "opened_at", "clicked_at")
    list_filter = ("campaign",)
    readonly_fields = ("id", "tracking_id", "sent_at", "opened_at", "clicked_at")
