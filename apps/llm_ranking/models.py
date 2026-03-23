import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class LLMRankingAudit(TimestampMixin):
    """
    A single LLM ranking audit run for a website.

    The audit queries multiple LLMs with generated prompts to measure how
    prominently the business appears in AI-generated answers.
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="llm_ranking_audits"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="llm_ranking_audits"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    # The prompts that were used for this audit
    prompts = models.JSONField(default=list)
    # Business context used for this audit (snapshot at time of run)
    business_name = models.CharField(max_length=200, blank=True)
    business_description = models.TextField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    keywords = models.JSONField(default=list)
    # Aggregate scores
    overall_score = models.IntegerField(default=0, db_index=True)  # 0-100
    mention_rate = models.FloatField(default=0.0)   # % of queries where business was mentioned
    avg_mention_rank = models.FloatField(default=0.0)  # avg position when mentioned (lower=better)
    # Which providers were queried
    providers_queried = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "llm_ranking_audit"
        ordering = ["-created_at"]

    def __str__(self):
        return f"LLMRankingAudit({self.website.name}, score={self.overall_score}, {self.status})"


class LLMRankingResult(TimestampMixin):
    """
    One result: a single LLM queried with a single prompt.
    Captures whether the business was mentioned and how prominently.
    """

    PROVIDER_CLAUDE = "claude"
    PROVIDER_GPT4 = "gpt4"
    PROVIDER_GEMINI = "gemini"
    PROVIDER_PERPLEXITY = "perplexity"
    PROVIDER_CHOICES = [
        (PROVIDER_CLAUDE, "Claude (Anthropic)"),
        (PROVIDER_GPT4, "GPT-4 (OpenAI)"),
        (PROVIDER_GEMINI, "Gemini (Google)"),
        (PROVIDER_PERPLEXITY, "Perplexity"),
    ]

    SENTIMENT_POSITIVE = "positive"
    SENTIMENT_NEUTRAL = "neutral"
    SENTIMENT_NEGATIVE = "negative"
    SENTIMENT_NOT_MENTIONED = "not_mentioned"
    SENTIMENT_CHOICES = [
        (SENTIMENT_POSITIVE, "Positive"),
        (SENTIMENT_NEUTRAL, "Neutral"),
        (SENTIMENT_NEGATIVE, "Negative"),
        (SENTIMENT_NOT_MENTIONED, "Not Mentioned"),
    ]

    audit = models.ForeignKey(LLMRankingAudit, on_delete=models.CASCADE, related_name="results")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, db_index=True)
    prompt = models.TextField()
    # Full LLM response text
    response_text = models.TextField(blank=True)
    # Whether the business name or a keyword appeared in the response
    is_mentioned = models.BooleanField(default=False, db_index=True)
    # Position of first mention among listed items (1=first, null=not mentioned)
    mention_rank = models.IntegerField(null=True, blank=True)
    # Sentiment of the mention
    sentiment = models.CharField(
        max_length=20, choices=SENTIMENT_CHOICES, default=SENTIMENT_NOT_MENTIONED
    )
    # 0-100 confidence score for the mention analysis
    confidence_score = models.FloatField(default=0.0)
    # Snippet of text around the first mention
    mention_context = models.TextField(blank=True)
    # Whether the LLM query succeeded (False = API error / rate limit)
    query_succeeded = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "llm_ranking_result"
        indexes = [
            models.Index(fields=["audit", "provider"]),
            models.Index(fields=["audit", "is_mentioned"]),
        ]

    def __str__(self):
        mentioned = "mentioned" if self.is_mentioned else "not mentioned"
        return f"LLMResult({self.provider}, {mentioned}, rank={self.mention_rank})"
