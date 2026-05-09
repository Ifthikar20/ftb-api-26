"""DRF serializers for the prompt_library REST surface."""
from __future__ import annotations

from rest_framework import serializers

from apps.prompt_library.models import (
    BrandPrompt,
    Industry,
    Prompt,
    PromptSampleEntry,
    PromptSampleRun,
)


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ("id", "slug", "name", "description")


class PromptSerializer(serializers.ModelSerializer):
    industry_slug = serializers.CharField(source="industry.slug", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = Prompt
        fields = (
            "id",
            "industry",
            "industry_slug",
            "text",
            "excerpt",
            "intent_bucket",
            "language",
            "source",
            "source_label",
            "source_url",
            "demand_score",
            "is_active",
            "created_at",
        )
        read_only_fields = ("demand_score", "created_at", "industry_slug", "source_label")


class PreviewSampleRequestSerializer(serializers.Serializer):
    industry_id = serializers.UUIDField()
    n = serializers.IntegerField(min_value=1, max_value=200, default=20)
    intent_mix = serializers.DictField(child=serializers.IntegerField(min_value=0), required=False)
    strategy = serializers.ChoiceField(
        choices=["stratified", "recent", "top_demand"], default="stratified"
    )


class UseLibrarySampleRequestSerializer(serializers.Serializer):
    industry_id = serializers.UUIDField()
    n = serializers.IntegerField(min_value=1, max_value=200, default=50)
    strategy = serializers.ChoiceField(
        choices=["stratified", "recent", "top_demand"], default="stratified"
    )
    seed = serializers.IntegerField(required=False)


class PromptSampleEntrySerializer(serializers.ModelSerializer):
    prompt = PromptSerializer(read_only=True)

    class Meta:
        model = PromptSampleEntry
        fields = ("rank", "prompt")


class PromptSampleRunSerializer(serializers.ModelSerializer):
    entries = serializers.SerializerMethodField()
    industry = IndustrySerializer(read_only=True)

    class Meta:
        model = PromptSampleRun
        fields = ("id", "industry", "seed", "strategy", "entries", "created_at")

    def get_entries(self, obj):
        qs = (
            PromptSampleEntry.objects.filter(sample_run=obj)
            .select_related("prompt", "prompt__industry")
            .order_by("rank")
        )
        return PromptSampleEntrySerializer(qs, many=True).data


class BrandPromptSerializer(serializers.ModelSerializer):
    prompt = PromptSerializer(read_only=True)
    prompt_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = BrandPrompt
        fields = ("id", "website", "prompt", "prompt_id", "notes", "created_at")
        read_only_fields = ("id", "website", "created_at")
