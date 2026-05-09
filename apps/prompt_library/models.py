"""
Demand-side prompt library models.

Stores broad-industry prompts mined from external sources (Reddit, SerpAPI,
LLM synthesis, etc.) and surfaces them to LLM Ranking audits via the
sampler service. Each audit can persist a ``PromptSampleRun`` recording
exactly which prompts were sampled and the seed used so a sample can be
reproduced or replayed.
"""
import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class PromptSource(models.TextChoices):
    REDDIT = "reddit", "Reddit"
    QUORA = "quora", "Quora"
    SERPAPI = "serpapi", "SerpAPI"
    DATAFORSEO = "dataforseo", "DataForSEO"
    LLM_SYNTH = "llm_synth", "LLM Synthesis"
    GSC_AGGREGATE = "gsc_aggregate", "GSC Aggregate"
    MANUAL = "manual", "Manual"


class IntentBucket(models.TextChoices):
    CATEGORY = "category", "Category"
    COMPARISON = "comparison", "Comparison"
    PROBLEM = "problem", "Problem"
    LOCAL = "local", "Local"


class Industry(TimestampMixin):
    """One row per supported broad industry. The taxonomy is intentionally
    flat (single level) — 20 broad buckets that map onto our prompt mining
    sources without sub-categorisation noise."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "prompt_library_industry"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Prompt(TimestampMixin):
    """A single demand-side prompt. ``text_hash`` is a sha256 of the
    normalised text so we can deduplicate exact matches cheaply at the
    DB layer; near-duplicates are caught upstream by the dedup service."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    industry = models.ForeignKey(
        Industry, related_name="prompts", on_delete=models.CASCADE
    )
    text = models.TextField()
    intent_bucket = models.CharField(max_length=20, choices=IntentBucket.choices)
    language = models.CharField(max_length=8, default="en")
    source = models.CharField(max_length=20, choices=PromptSource.choices)
    source_url = models.URLField(blank=True, max_length=500)
    excerpt = models.TextField(blank=True)
    demand_score = models.FloatField(default=0.0, db_index=True)
    is_active = models.BooleanField(default=True)
    text_hash = models.CharField(max_length=64, db_index=True)
    # Templated body with {{ variable }} placeholders. When non-empty,
    # `text` is treated as a denormalised preview of the template.
    template_text = models.TextField(
        blank=True,
        help_text="Prompt body with {{ variable }} placeholders. If empty, falls back to text.",
    )
    template_variables = models.JSONField(
        default=list, blank=True,
        help_text="Auto-extracted list of placeholder names",
    )
    STYLE_CHOICES = [
        ("question", "Question"),
        ("story", "Story"),
        ("comparison", "Comparison"),
        ("local", "Local"),
        ("how_to", "How-to"),
        ("listicle", "Listicle"),
    ]
    style = models.CharField(
        max_length=24, choices=STYLE_CHOICES, default="question", db_index=True,
    )
    effectiveness_score = models.FloatField(
        default=0.0, db_index=True,
        help_text="Cached 0-1 score from past audit performance",
    )
    effectiveness_components = models.JSONField(
        default=dict, blank=True,
        help_text="Per-axis breakdown: visibility_hit_rate, citation_yield, claim_yield, coverage_breadth",
    )
    runs_count = models.IntegerField(
        default=0, help_text="Number of audit runs that used this prompt",
    )
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "prompt_library_prompt"
        indexes = [
            models.Index(fields=["industry", "intent_bucket", "is_active"]),
        ]
        unique_together = [("industry", "text_hash")]
        ordering = ["-demand_score", "-created_at"]

    def __str__(self):
        return f"Prompt({self.intent_bucket}, {self.text[:60]!r})"


class PromptVariation(TimestampMixin):
    """Paraphrase of a parent prompt. Embeddings stored as a JSON list to
    match the convention used in apps.rag — pgvector is intentionally
    avoided so the deployment topology stays unchanged."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_prompt = models.ForeignKey(
        Prompt, related_name="variations", on_delete=models.CASCADE
    )
    text = models.TextField()
    text_hash = models.CharField(max_length=64)
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "prompt_library_promptvariation"
        unique_together = [("parent_prompt", "text_hash")]


class IndustryTrend(TimestampMixin):
    """Cached Google Trends snapshot for a single industry.

    Pulled via :mod:`apps.prompt_library.services.trends_service` and
    refreshed when older than 24h. We keep the data as JSON arrays
    rather than per-week rows because consumers always read the whole
    series at once and pytrends responses are small.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    industry = models.OneToOneField(
        Industry, related_name="trend", on_delete=models.CASCADE
    )
    # interest_over_time: list of {"week": "YYYY-MM-DD", "value": 0..100}
    interest_over_time = models.JSONField(default=list, blank=True)
    # top_regions: list of {"code": "US", "name": "United States", "value": 0..100}
    top_regions = models.JSONField(default=list, blank=True)
    keyword_used = models.CharField(max_length=120, blank=True)
    refreshed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = "prompt_library_industrytrend"

    def __str__(self):
        return f"IndustryTrend({self.industry.slug})"


class BrandPrompt(TimestampMixin):
    """A library prompt a user has added to their website's brand prompt set.

    Merged with library samples when an audit runs so users always test
    against the prompts they care about. Hard-delete is the correct
    semantic — removing a row means "stop testing this prompt".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website",
        related_name="brand_prompts",
        on_delete=models.CASCADE,
    )
    prompt = models.ForeignKey(
        Prompt, related_name="brand_prompts", on_delete=models.CASCADE
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "prompt_library_brandprompt"
        unique_together = [("website", "prompt")]
        indexes = [models.Index(fields=["website", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"BrandPrompt(website={self.website_id}, prompt={self.prompt_id})"


class PromptSampleRun(TimestampMixin):
    """Per-audit snapshot: which prompts were sampled and how. The
    ``seed`` field makes the sample reproducible — re-running the
    sampler with the same (industry, seed, strategy, n) yields the
    same prompt set."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit_run = models.OneToOneField(
        "llm_ranking.LLMRankingAudit",
        on_delete=models.CASCADE,
        related_name="prompt_sample_run",
    )
    industry = models.ForeignKey(Industry, on_delete=models.PROTECT)
    seed = models.IntegerField()
    strategy = models.CharField(max_length=32, default="stratified")
    sampled_prompts = models.ManyToManyField(
        Prompt, through="PromptSampleEntry", related_name="sample_runs"
    )

    class Meta:
        db_table = "prompt_library_promptsamplerun"
        ordering = ["-created_at"]


class PromptSampleEntry(models.Model):
    """Through table — preserves the rank/order of each prompt in the
    sample so the UI can show the sequence used by the audit."""

    sample_run = models.ForeignKey(PromptSampleRun, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.PROTECT)
    rank = models.IntegerField()

    class Meta:
        db_table = "prompt_library_promptsampleentry"
        unique_together = [("sample_run", "prompt")]
        ordering = ["rank"]


class PromptVariableSet(TimestampMixin):
    """Per-website templating dictionary. One row per website."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.OneToOneField(
        "websites.Website",
        related_name="prompt_variables",
        on_delete=models.CASCADE,
    )
    variables = models.JSONField(
        default=dict, blank=True,
        help_text="key -> value, e.g. {'location': 'Dallas', 'sales_item': 'medical board'}",
    )

    class Meta:
        db_table = "prompt_library_promptvariableset"

    def __str__(self):
        return f"PromptVariableSet({self.website_id})"
