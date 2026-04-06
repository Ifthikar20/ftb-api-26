from django.contrib import admin

from .models import SocialLead, SocialLeadSource


@admin.register(SocialLeadSource)
class SocialLeadSourceAdmin(admin.ModelAdmin):
    list_display = ["platform", "label", "website", "is_active", "total_leads_imported", "last_synced_at"]
    list_filter = ["platform", "is_active"]
    search_fields = ["label", "account_id", "form_id"]


@admin.register(SocialLead)
class SocialLeadAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "phone", "source", "is_processed", "created_at"]
    list_filter = ["source__platform", "is_processed"]
    search_fields = ["first_name", "last_name", "email", "phone"]
