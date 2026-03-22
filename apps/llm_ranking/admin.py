from django.contrib import admin
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult


class LLMRankingResultInline(admin.TabularInline):
    model = LLMRankingResult
    extra = 0
    readonly_fields = ("provider", "prompt", "is_mentioned", "mention_rank", "sentiment", "confidence_score", "query_succeeded")
    can_delete = False


@admin.register(LLMRankingAudit)
class LLMRankingAuditAdmin(admin.ModelAdmin):
    list_display = ("id", "website", "business_name", "status", "overall_score", "mention_rate", "created_at")
    list_filter = ("status",)
    search_fields = ("business_name", "website__name")
    readonly_fields = ("id", "created_at", "updated_at", "completed_at")
    ordering = ("-created_at",)
    inlines = [LLMRankingResultInline]


@admin.register(LLMRankingResult)
class LLMRankingResultAdmin(admin.ModelAdmin):
    list_display = ("id", "audit", "provider", "is_mentioned", "mention_rank", "sentiment", "query_succeeded")
    list_filter = ("provider", "is_mentioned", "sentiment", "query_succeeded")
    search_fields = ("prompt", "response_text")
    ordering = ("-created_at",)
