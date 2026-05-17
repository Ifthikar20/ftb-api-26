"""DRF serializers for the content_studio API."""
from rest_framework import serializers

from apps.content_studio.models import ContentBrief, ContentDraft


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
