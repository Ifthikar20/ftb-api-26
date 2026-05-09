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
    demand_score = models.FloatField(default=0.0, db_index=True)
    is_active = models.BooleanField(default=True)
    text_hash = models.CharField(max_length=64, db_index=True)

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
