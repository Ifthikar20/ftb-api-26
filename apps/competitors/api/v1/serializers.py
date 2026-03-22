from rest_framework import serializers

from apps.competitors.models import Competitor, CompetitorChange, CompetitorSnapshot


class CompetitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competitor
        fields = [
            "id", "competitor_url", "name", "auto_detected", "estimated_traffic",
            "domain_authority", "threat_level", "last_crawled_at", "created_at",
        ]
        read_only_fields = ["id", "auto_detected", "last_crawled_at", "created_at"]


class CompetitorSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitorSnapshot
        fields = ["id", "captured_at", "traffic_estimate", "keyword_count", "backlink_count", "metrics"]


class CompetitorChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitorChange
        fields = ["id", "change_type", "detail", "detected_at"]
