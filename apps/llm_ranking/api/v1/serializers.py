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
            "run_id", "is_linked", "competitors_mentioned",
            "primary_recommendation", "citations",
            "extraction_model", "extraction_version",
        ]
        read_only_fields = fields


class LLMRankingAuditSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    extraction_method_display = serializers.CharField(
        source="get_extraction_method_display", read_only=True
    )
    results = LLMRankingResultSerializer(many=True, read_only=True)

    class Meta:
        model = LLMRankingAudit
        fields = [
            "id", "status", "status_display",
            "business_name", "business_description", "industry", "location", "keywords",
            "prompts", "overall_score", "mention_rate", "avg_mention_rank",
            "mention_rate_ci_lower", "mention_rate_ci_upper",
            "runs_per_query", "extraction_method", "extraction_method_display",
            "providers_queried", "queries_completed", "total_queries",
            "started_at", "completed_at", "created_at",
            "results",
        ]
        read_only_fields = [
            "id", "status", "status_display", "overall_score", "mention_rate",
            "avg_mention_rank", "mention_rate_ci_lower", "mention_rate_ci_upper",
            "extraction_method", "extraction_method_display",
            "providers_queried", "queries_completed", "total_queries",
            "started_at", "completed_at", "created_at",
            "results",
        ]


class LLMRankingAuditListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view — omits per-result details."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LLMRankingAudit
        fields = [
            "id", "status", "status_display",
            "business_name", "industry", "location",
            "overall_score", "mention_rate", "avg_mention_rank",
            "mention_rate_ci_lower", "mention_rate_ci_upper",
            "providers_queried", "queries_completed", "total_queries",
            "started_at", "completed_at", "created_at",
        ]
        read_only_fields = fields


class RunAuditSerializer(serializers.Serializer):
    """Input serializer for creating a new audit."""
    business_name = serializers.CharField(max_length=200)
    business_description = serializers.CharField(required=False, default="", allow_blank=True)
    industry = serializers.CharField(max_length=100)
    location = serializers.CharField(max_length=200, required=False, default="", allow_blank=True)
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
    # Which providers to query (defaults to all)
    providers = serializers.ListField(
        child=serializers.ChoiceField(choices=["claude", "gpt4", "gemini", "perplexity"]),
        required=False,
        default=list,
    )
    # Intent themes (recommendation, comparison, ...) used to filter the
    # PromptLibrary mix when generating prompts.
    themes = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            "recommendation", "comparison", "alternatives", "use_case",
            "category", "persona", "review", "local",
        ]),
        required=False,
        default=list,
        max_length=8,
    )
