"""DRF serializers for the prompt_library REST surface."""
from __future__ import annotations

from rest_framework import serializers

from apps.prompt_library.models import (
    BrandPrompt,
    Industry,
    Prompt,
    PromptSampleEntry,
    PromptSampleRun,
    PromptVariableSet,
)


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ("id", "slug", "name", "description")


class PromptSerializer(serializers.ModelSerializer):
    industry_slug = serializers.CharField(source="industry.slug", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    style_label = serializers.CharField(source="get_style_display", read_only=True)

    class Meta:
        model = Prompt
        fields = (
            "id",
            "industry",
            "industry_slug",
            "text",
            "excerpt",
            "template_text",
            "template_variables",
            "intent_bucket",
            "language",
            "source",
            "source_label",
            "source_url",
            "style",
            "style_label",
            "demand_score",
            "effectiveness_score",
            "effectiveness_components",
            "runs_count",
            "last_used_at",
            "is_active",
            "created_at",
        )
        read_only_fields = (
            "demand_score",
            "effectiveness_score",
            "effectiveness_components",
            "runs_count",
            "last_used_at",
            "created_at",
            "industry_slug",
            "source_label",
            "style_label",
            "template_variables",
        )


class PromptCreateSerializer(serializers.Serializer):
    """Payload for the per-website "new prompt" endpoint."""

    industry_id = serializers.UUIDField(required=False)
    template_text = serializers.CharField()
    intent_bucket = serializers.CharField(required=False, default="category")
    style = serializers.CharField(required=False, default="question")
    text = serializers.CharField(required=False, allow_blank=True)


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


class PromptVariableSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVariableSet
        fields = ("variables", "updated_at")


class AutoTemplateRequestSerializer(serializers.Serializer):
    raw_text = serializers.CharField()


class SmokeTestRequestSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=["claude", "gpt4", "gemini", "perplexity"], default="claude",
    )
    website_id = serializers.UUIDField()


class SynthesizeRequestSerializer(serializers.Serializer):
    industry_id = serializers.UUIDField()
    count = serializers.IntegerField(min_value=1, max_value=50, default=10)
    style = serializers.ChoiceField(
        choices=["question", "story", "comparison", "local", "how_to", "listicle"],
        default="question",
    )
    examples = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )


class VariableSetUpdateSerializer(serializers.Serializer):
    variables = serializers.DictField(child=serializers.CharField(allow_blank=True))
