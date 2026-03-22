from rest_framework import serializers
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult


class LLMRankingResultSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source="get_provider_display", read_only=True)
    sentiment_display = serializers.CharField(source="get_sentiment_display", read_only=True)

    class Meta:
        model = LLMRankingResult
        fields = [
            "id", "provider", "provider_display", "prompt",
            "response_text", "is_mentioned", "mention_rank",
            "sentiment", "sentiment_display", "confidence_score",
            "mention_context", "query_succeeded", "error_message",
        ]
        read_only_fields = fields


class LLMRankingAuditSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    results = LLMRankingResultSerializer(many=True, read_only=True)

    class Meta:
        model = LLMRankingAudit
        fields = [
            "id", "status", "status_display",
            "business_name", "business_description", "industry", "keywords",
            "prompts", "overall_score", "mention_rate", "avg_mention_rank",
            "providers_queried", "completed_at", "created_at",
            "results",
        ]
        read_only_fields = [
            "id", "status", "status_display", "overall_score", "mention_rate",
            "avg_mention_rank", "providers_queried", "completed_at", "created_at",
            "results",
        ]


class LLMRankingAuditListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view — omits per-result details."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LLMRankingAudit
        fields = [
            "id", "status", "status_display",
            "business_name", "industry",
            "overall_score", "mention_rate", "avg_mention_rank",
            "providers_queried", "completed_at", "created_at",
        ]
        read_only_fields = fields


class RunAuditSerializer(serializers.Serializer):
    """Input serializer for creating a new audit."""
    business_name = serializers.CharField(max_length=200)
    business_description = serializers.CharField(required=False, default="", allow_blank=True)
    industry = serializers.CharField(max_length=100)
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        max_length=20,
    )
    use_case = serializers.CharField(max_length=200, required=False, default="", allow_blank=True)
    # Optionally supply custom prompts instead of auto-generating them
    custom_prompts = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
        max_length=10,
    )
