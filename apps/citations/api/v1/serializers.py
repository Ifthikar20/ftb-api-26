"""DRF serializers for the citations API."""
from rest_framework import serializers

from apps.citations.models import (
    Citation,
    SourceClass,
    SourceInfluenceSnapshot,
)


class CitationSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="result.provider", read_only=True)
    source_class_label = serializers.CharField(
        source="get_source_class_display", read_only=True,
    )

    class Meta:
        model = Citation
        fields = (
            "id", "audit", "result", "provider",
            "url", "normalized_url", "domain", "apex_domain",
            "source_class", "source_class_label",
            "extraction_method", "confidence", "position",
            "title", "snippet",
            "is_target", "is_competitor",
            "created_at",
        )
        read_only_fields = fields


class SourceInfluenceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceInfluenceSnapshot
        fields = (
            "id", "provider", "industry", "website",
            "period_start", "period_end",
            "total_citations", "breakdown", "top_domains",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class SourceClassChoiceSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()

    @classmethod
    def all(cls):
        return [{"value": k, "label": v} for k, v in SourceClass.choices]
