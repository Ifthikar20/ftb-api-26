"""DRF serializers for the content_studio API."""
from rest_framework import serializers

from apps.content_studio.models import (
    ContentBrief,
    ContentDraft,
    PublishLog,
    PublishTarget,
    ROIAttribution,
)


class ContentBriefSerializer(serializers.ModelSerializer):
    grounded_fact_ids = serializers.SerializerMethodField()

    class Meta:
        model = ContentBrief
        fields = (
            "id", "website",
            "gap_type", "impact_score",
            "target_format", "target_prompt",
            "target_source_class",
            "headline", "description",
            "suggested_structure", "target_keywords",
            "grounded_fact_ids",
            "status",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_grounded_fact_ids(self, obj):
        return [str(f.id) for f in obj.grounded_facts.all()]


class ContentDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentDraft
        fields = (
            "id", "brief", "website",
            "title", "body_markdown", "body_html", "json_ld",
            "word_count",
            "voice_score", "voice_notes",
            "accuracy_score", "accuracy_notes",
            "status", "generated_by", "revision",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "brief", "website",
            "word_count",
            "voice_score", "voice_notes",
            "accuracy_score", "accuracy_notes",
            "generated_by", "revision",
            "created_at", "updated_at",
        )


class PublishTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishTarget
        fields = (
            "id", "website", "provider", "label", "config",
            "is_default", "is_active",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "website", "created_at", "updated_at")


class PublishLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishLog
        fields = (
            "id", "draft", "target",
            "status", "external_id", "external_url",
            "error_message", "request_payload", "response_payload",
            "created_at",
        )
        read_only_fields = fields


class ROIAttributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ROIAttribution
        fields = (
            "id", "draft", "website",
            "measured_at", "days_since_publish",
            "visibility_before", "visibility_after", "visibility_lift",
            "citation_count_before", "citation_count_after",
            "accuracy_lift",
            "affected_prompts",
            "created_at",
        )
        read_only_fields = fields
