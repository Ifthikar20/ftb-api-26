"""DRF serializers for the brand_vault API."""
from rest_framework import serializers

from apps.brand_vault.models import (
    BrandFact, FactRevision, SafetyAlert, SafetyPrompt, ToneSample,
)


class FactRevisionSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = FactRevision
        fields = (
            "id", "action", "before", "after",
            "actor_user", "actor_email", "created_at",
        )
        read_only_fields = fields

    def get_actor_email(self, obj):
        return getattr(obj.actor_user, "email", "") or ""


class BrandFactSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = BrandFact
        fields = (
            "id", "website",
            "subject", "predicate", "object",
            "source_chunk", "source_url", "extracted_by",
            "confidence", "status",
            "version_from", "version_to", "superseded_by",
            "product_line", "topic", "audience",
            "is_current",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_is_current(self, obj):
        return obj.version_to is None


class BrandFactDetailSerializer(BrandFactSerializer):
    revisions = FactRevisionSerializer(many=True, read_only=True)

    class Meta(BrandFactSerializer.Meta):
        fields = BrandFactSerializer.Meta.fields + ("revisions",)
        read_only_fields = fields


class BrandFactEditSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=300)
    predicate = serializers.CharField(max_length=200)
    object = serializers.CharField()


class ToneSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToneSample
        fields = (
            "id", "website", "source_chunk",
            "text", "text_hash", "word_count",
            "created_at",
        )
        read_only_fields = fields


class SafetyPromptSerializer(serializers.ModelSerializer):
    hits = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = SafetyPrompt
        fields = (
            "id", "website", "text", "status",
            "hits", "created_at", "updated_at",
        )
        read_only_fields = ("id", "website", "hits", "created_at", "updated_at")


class SafetyPromptCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=500)


class SafetyAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyAlert
        fields = (
            "id", "website", "prompt",
            "model", "prompt_text", "snippet",
            "issue", "detail", "severity", "status",
            "detected_at", "resolved_at",
            "created_at",
        )
        read_only_fields = fields


class FactImportItemSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=300)
    predicate = serializers.CharField(max_length=200)
    object = serializers.CharField()
    product_line = serializers.CharField(max_length=120, required=False, allow_blank=True)
    topic = serializers.CharField(max_length=120, required=False, allow_blank=True)
    confidence = serializers.FloatField(required=False, default=0.9)
    source_url = serializers.URLField(required=False, allow_blank=True, max_length=1000)
