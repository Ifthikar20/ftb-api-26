from rest_framework import serializers
from apps.leads.models import Lead, LeadNote, LeadSegment, ScoringConfig, EmailCampaign, CampaignRecipient


class LeadSerializer(serializers.ModelSerializer):
    visitor_fingerprint = serializers.CharField(source="visitor.fingerprint_hash", read_only=True)
    geo_country = serializers.CharField(source="visitor.geo_country", read_only=True)
    device_type = serializers.CharField(source="visitor.device_type", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "score", "status", "email", "name", "company", "source",
            "visitor_fingerprint", "geo_country", "device_type",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "score", "created_at", "updated_at"]


class LeadNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = LeadNote
        fields = ["id", "content", "author_name", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]


class LeadSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSegment
        fields = ["id", "name", "rules", "created_at"]
        read_only_fields = ["id", "created_at"]


class ScoringConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoringConfig
        fields = ["id", "weights", "threshold", "ml_model_version", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class EmailCampaignSerializer(serializers.ModelSerializer):
    open_rate = serializers.FloatField(read_only=True)
    click_rate = serializers.FloatField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = EmailCampaign
        fields = [
            "id", "subject", "body", "status", "segment", "canva_design_url",
            "sent_at", "recipient_count", "open_count", "click_count",
            "open_rate", "click_rate", "mailchimp_campaign_id",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "sent_at", "recipient_count", "open_count", "click_count",
            "open_rate", "click_rate", "mailchimp_campaign_id", "created_by_name",
            "created_at", "updated_at",
        ]


class CampaignRecipientSerializer(serializers.ModelSerializer):
    lead_email = serializers.EmailField(source="lead.email", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)

    class Meta:
        model = CampaignRecipient
        fields = ["id", "lead", "lead_email", "lead_name", "status", "sent_at", "opened_at", "clicked_at"]
        read_only_fields = ["id", "lead_email", "lead_name", "status", "sent_at", "opened_at", "clicked_at"]
