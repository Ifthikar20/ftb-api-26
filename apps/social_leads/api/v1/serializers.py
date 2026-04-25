from rest_framework import serializers

from apps.social_leads.models import SocialLead, SocialLeadSource


class SocialLeadSourceSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source="get_platform_display", read_only=True)

    class Meta:
        model = SocialLeadSource
        fields = [
            "id", "platform", "platform_display", "label", "is_active",
            "account_id", "form_id", "campaign_name",
            "webhook_verify_token", "total_leads_imported", "last_synced_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "platform_display", "total_leads_imported",
            "last_synced_at", "created_at", "updated_at",
        ]


class SocialLeadSerializer(serializers.ModelSerializer):
    platform = serializers.CharField(source="source.platform", read_only=True)
    platform_display = serializers.CharField(source="source.get_platform_display", read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = SocialLead
        fields = [
            "id", "platform", "platform_display", "full_name",
            "first_name", "last_name", "email", "phone",
            "company", "job_title", "linkedin_profile",
            "form_data", "is_processed",
            "lead", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "platform", "platform_display", "full_name",
            "is_processed", "lead",
            "created_at", "updated_at",
        ]
