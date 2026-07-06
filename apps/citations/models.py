"""Citation tracking models.

Phase 2 of the GEO platform: persist every URL the LLM cited in a ranking
result, classify the source domain (reddit, news, docs, etc.) and roll up
share-of-citation per provider/industry/website for the dashboard.
"""
import uuid

from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class SourceClass(models.TextChoices):
    REDDIT = "reddit", "Reddit"
    QUORA = "quora", "Quora"
    STACKOVERFLOW = "stackoverflow", "Stack Overflow"
    NEWS = "news", "News"
    WIKIPEDIA = "wikipedia", "Wikipedia"
    BLOG = "blog", "Blog"
    FORUM = "forum", "Forum"
    DOCS = "docs", "Documentation"
    SOCIAL = "social", "Social"
    YOUTUBE = "youtube", "YouTube"
    PODCAST = "podcast", "Podcast"
    GOV = "gov", "Government"
    EDU = "edu", "Education"
    YOUR_SITE = "your_site", "Your Site"
    COMPETITOR_SITE = "competitor_site", "Competitor"
    OTHER = "other", "Other"


class CitationExtractionMethod(models.TextChoices):
    NATIVE = "native", "Native"
    GROUNDING = "grounding", "Grounding"
    REGEX = "regex", "Regex"
    LLM_ASSISTED = "llm_assisted", "LLM Assisted"


class Citation(TimestampMixin):
    """One URL cited by an LLM in a ranking result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(
        "llm_ranking.LLMRankingResult",
        related_name="extracted_citations",
        on_delete=models.CASCADE,
    )
    audit = models.ForeignKey(
        "llm_ranking.LLMRankingAudit",
        related_name="extracted_citations",
        on_delete=models.CASCADE,
    )
    url = models.URLField(max_length=2000)
    normalized_url = models.CharField(max_length=2000, db_index=True)
    domain = models.CharField(max_length=300, db_index=True)
    apex_domain = models.CharField(max_length=300, db_index=True)
    source_class = models.CharField(
        max_length=24, choices=SourceClass.choices, db_index=True,
        default=SourceClass.OTHER,
    )
    extraction_method = models.CharField(
        max_length=16, choices=CitationExtractionMethod.choices,
        default=CitationExtractionMethod.REGEX,
    )
    confidence = models.FloatField(default=1.0)
    position = models.IntegerField(null=True, blank=True)
    # Number of times this source is *explicitly* referenced in the answer
    # text (numbered marker like [2] for native/grounding sources, or the
    # literal URL appearing in prose for regex hits). 0 means the page was
    # retrieved as a candidate source but never cited in the response.
    reference_count = models.IntegerField(default=0)
    title = models.CharField(max_length=500, blank=True)
    snippet = models.TextField(blank=True)
    is_target = models.BooleanField(default=False)
    is_competitor = models.BooleanField(default=False)

    class Meta:
        db_table = "citations_citation"
        indexes = [
            models.Index(fields=["audit", "source_class"]),
            models.Index(fields=["apex_domain", "source_class"]),
            models.Index(fields=["result", "position"]),
        ]
        unique_together = [("result", "normalized_url")]

    def __str__(self):
        return f"Citation({self.apex_domain}, {self.source_class})"


class DomainClassification(TimestampMixin):
    """Cache of apex_domain -> source_class. Populated lazily by the classifier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    apex_domain = models.CharField(max_length=300, unique=True)
    source_class = models.CharField(max_length=24, choices=SourceClass.choices)
    notes = models.TextField(blank=True)
    classified_by = models.CharField(max_length=24, default="rules")

    class Meta:
        db_table = "citations_domainclassification"

    def __str__(self):
        return f"{self.apex_domain} -> {self.source_class}"


class SourceInfluenceSnapshot(TimestampMixin):
    """Daily rollup. (provider x industry x website?) over a date range."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32)
    industry = models.ForeignKey(
        "prompt_library.Industry", null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    website = models.ForeignKey(
        "websites.Website", null=True, blank=True, on_delete=models.CASCADE,
        help_text="If set, this snapshot is per-tenant; if null, global.",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    total_citations = models.IntegerField(default=0)
    breakdown = models.JSONField(default=dict)
    top_domains = models.JSONField(default=list)

    class Meta:
        db_table = "citations_sourceinfluencesnapshot"
        unique_together = [("provider", "industry", "website", "period_start", "period_end")]
        indexes = [
            models.Index(fields=["provider", "period_end"]),
            models.Index(fields=["website", "period_end"]),
        ]

    def __str__(self):
        scope = self.website_id or self.industry_id or "global"
        return f"Influence({self.provider}, {scope}, {self.period_end})"


class SourceScanStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETE = "complete", "Complete"
    FAILED = "failed", "Failed"


class SourceScan(TimestampMixin):
    """One Source Intelligence run: query -> SERP -> content -> sentiment.

    Fetches the top web results for a query from an AI-era search index
    (Perplexity), reads the content behind each result (Reddit threads
    via the public JSON API, regular pages via the SSRF-guarded
    fetcher), and extracts brand mentions and sentiment with a cheap
    LLM. `brands` holds the aggregated share-of-voice rollup.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", related_name="source_scans", on_delete=models.CASCADE
    )
    query = models.CharField(max_length=500)
    provider = models.CharField(max_length=32, default="perplexity")
    status = models.CharField(
        max_length=16, choices=SourceScanStatus.choices,
        default=SourceScanStatus.PENDING, db_index=True,
    )
    error = models.TextField(blank=True)
    results_count = models.IntegerField(default=0)
    analyzed_count = models.IntegerField(default=0)
    # Aggregate: [{"name", "mentions", "weighted_score", "sentiment",
    #              "results_present_in", "top_quote"}] sorted by weight.
    brands = models.JSONField(default=list, blank=True)
    # True when the scan's own website brand was found anywhere.
    own_brand_present = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "citations_sourcescan"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["website", "-created_at"])]

    def __str__(self):
        return f"SourceScan({self.query[:40]!r}, {self.status})"


class SourceScanResult(TimestampMixin):
    """One ranked URL from a SourceScan, plus what we learned from it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(
        SourceScan, related_name="results", on_delete=models.CASCADE
    )
    rank = models.IntegerField()
    url = models.URLField(max_length=2000)
    domain = models.CharField(max_length=300, db_index=True)
    source_class = models.CharField(
        max_length=24, choices=SourceClass.choices, default=SourceClass.OTHER
    )
    serp_title = models.CharField(max_length=500, blank=True)
    serp_snippet = models.TextField(blank=True)
    # Publication dates as reported by the search engine (may be absent).
    published_at = models.DateField(null=True, blank=True)
    last_updated_at = models.DateField(null=True, blank=True)
    # SERP relevance gate: off-topic results (e.g. designer "bags" for a
    # "bagels" query) are excluded from fetching, analysis, and rollups.
    relevant = models.BooleanField(default=True)
    relevance_note = models.CharField(max_length=200, blank=True)
    # ok | blocked | error | skipped
    fetch_status = models.CharField(max_length=16, default="skipped")
    # reddit | page
    content_kind = models.CharField(max_length=16, blank=True)
    word_count = models.IntegerField(default=0)
    # Per-result extraction: [{"name", "sentiment" (-1..1), "mentions",
    #                          "weight", "quotes": [..]}]
    brands = models.JSONField(default=list, blank=True)
    analysis_error = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "citations_sourcescanresult"
        ordering = ["rank"]
        unique_together = [("scan", "rank")]

    def __str__(self):
        return f"SourceScanResult(#{self.rank} {self.domain})"
