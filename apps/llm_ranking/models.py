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
    # Progress tracking for batch job
    queries_completed = models.IntegerField(default=0)
    total_queries = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    # Statistics: number of replicates per (prompt, provider) — N=1 is the current default
    runs_per_query = models.IntegerField(default=1)
    # 95% Wilson CI on the overall mention_rate (percent 0-100)
    mention_rate_ci_lower = models.FloatField(default=0.0)
    mention_rate_ci_upper = models.FloatField(default=0.0)
    # How per-response extraction was performed
    EXTRACTION_HEURISTIC = "heuristic"
    EXTRACTION_LLM = "llm"
    EXTRACTION_CHOICES = [
        (EXTRACTION_HEURISTIC, "Heuristic (regex + lexicon)"),
        (EXTRACTION_LLM, "LLM (Haiku-class model)"),
    ]
    extraction_method = models.CharField(
        max_length=20, choices=EXTRACTION_CHOICES, default=EXTRACTION_HEURISTIC
    )

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
    # Replicate index within a (prompt, provider) pair — 0 for single-run audits
    run_id = models.IntegerField(default=0)
    # Whether the business name appeared as a hyperlink in the response
    is_linked = models.BooleanField(default=False)
    # List of competitor brands mentioned in this response
    # Each entry: {"name": str, "position": int|null, "linked": bool}
    competitors_mentioned = models.JSONField(default=list, blank=True)
    # Which brand the LLM explicitly recommended (if any)
    primary_recommendation = models.CharField(max_length=200, blank=True)
    # URLs cited in the response
    citations = models.JSONField(default=list, blank=True)
    # Which model + prompt version was used to extract structured data
    extraction_model = models.CharField(max_length=100, blank=True)
    extraction_version = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "llm_ranking_result"
        indexes = [
            models.Index(fields=["audit", "provider"]),
            models.Index(fields=["audit", "is_mentioned"]),
        ]

    def __str__(self):
        mentioned = "mentioned" if self.is_mentioned else "not mentioned"
        return f"LLMResult({self.provider}, {mentioned}, rank={self.mention_rank})"


class LLMRankingSchedule(TimestampMixin):
    """
    Per-website periodic LLM ranking audit schedule.

    When enabled, a Celery Beat task checks for schedules whose next_run_at
    has passed and creates + queues a new LLMRankingAudit automatically.
    """

    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_BIWEEKLY = "biweekly"
    FREQUENCY_MONTHLY = "monthly"
    FREQUENCY_CHOICES = [
        (FREQUENCY_WEEKLY, "Weekly"),
        (FREQUENCY_BIWEEKLY, "Every 2 Weeks"),
        (FREQUENCY_MONTHLY, "Monthly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.OneToOneField(
        "websites.Website", on_delete=models.CASCADE, related_name="llm_ranking_schedule"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    is_enabled = models.BooleanField(default=True, db_index=True)
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default=FREQUENCY_WEEKLY
    )
    # Business context for auto-generated audits
    business_name = models.CharField(max_length=200)
    business_description = models.TextField(blank=True)
    industry = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    keywords = models.JSONField(default=list)
    providers = models.JSONField(
        default=list,
        help_text="LLM providers to query. Empty = all.",
    )
    # Scheduling fields
    next_run_at = models.DateTimeField(db_index=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "llm_ranking_schedule"

    def __str__(self):
        status = "enabled" if self.is_enabled else "disabled"
        return f"LLMSchedule({self.website.name}, {self.frequency}, {status})"
