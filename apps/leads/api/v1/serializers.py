from rest_framework import serializers
from apps.leads.models import Lead, LeadNote, LeadSegment, ScoringConfig


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
