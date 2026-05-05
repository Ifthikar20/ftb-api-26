"""
Per-user knowledge base for retrieval-augmented prompt construction.

A KnowledgeSource is one URL the user (or their automated crawler) added
to the knowledge base for a website. KnowledgeChunks are the embedded
text segments extracted from that source — they are what the retriever
searches at query time.

Design notes:
- Embeddings are stored as JSON arrays. Postgres JSONB handles this
  efficiently for the per-user corpus sizes we expect (< 10K chunks per
  website). Avoids pulling pgvector into the deployment.
- Cosine similarity is computed in Python on a candidate set scoped to
  (user, website). The scope keeps the candidate set small enough that
  brute-force scoring is fast (sub-100ms for a few thousand chunks).
- The "learns" property comes from accumulating chunks across audits +
  manual additions. Every audit can ingest its own enrichment context
  back into the knowledge base, so subsequent audits draw from a richer
  seed each time.
"""
import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class KnowledgeSource(TimestampMixin):
    """One ingested URL belonging to a (user, website) knowledge base."""

    KIND_HOMEPAGE = "homepage"
    KIND_BLOG = "blog"
    KIND_PRODUCT = "product"
    KIND_DOCS = "docs"
    KIND_REVIEW = "review"
    KIND_OTHER = "other"
    KIND_AUDIT_CONTEXT = "audit_context"
    KIND_CHOICES = [
        (KIND_HOMEPAGE, "Homepage"),
        (KIND_BLOG, "Blog post"),
        (KIND_PRODUCT, "Product page"),
        (KIND_DOCS, "Documentation"),
        (KIND_REVIEW, "Review / mention"),
        (KIND_OTHER, "Other"),
        (KIND_AUDIT_CONTEXT, "Audit context"),
    ]

    STATUS_PENDING = "pending"
    STATUS_INGESTING = "ingesting"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_INGESTING, "Ingesting"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_sources",
    )
    website = models.ForeignKey(
        "websites.Website",
        on_delete=models.CASCADE,
        related_name="knowledge_sources",
    )
    url = models.URLField(max_length=2000)
    title = models.CharField(max_length=500, blank=True)
    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES, default=KIND_OTHER, db_index=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
    )
    # Content fingerprint so we don't re-embed unchanged pages.
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    chunk_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    last_ingested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rag_knowledge_source"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "website", "url"],
                name="uq_rag_source_user_website_url",
            ),
        ]
        # Explicit index names match the hand-written 0001_initial
        # migration so Django's autodetector doesn't propose a no-op
        # rename migration on every makemigrations.
        indexes = [
            models.Index(fields=["user", "website"], name="rag_kn_sou_user_website_idx"),
            models.Index(fields=["website", "kind"], name="rag_kn_sou_website_kind_idx"),
        ]

    def __str__(self):
        return f"KnowledgeSource({self.url[:60]}, {self.status})"


class KnowledgeChunk(TimestampMixin):
    """One embedded text segment from a KnowledgeSource."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        KnowledgeSource, on_delete=models.CASCADE, related_name="chunks",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_chunks",
    )
    website = models.ForeignKey(
        "websites.Website",
        on_delete=models.CASCADE,
        related_name="knowledge_chunks",
    )
    # Order of this chunk within its source (0-indexed).
    chunk_index = models.IntegerField(default=0)
    # Raw text — kept compact via the chunker (≤ ~400 words).
    text = models.TextField()
    # Embedding vector. List of floats. Length = embedding model dim
    # (1536 for OpenAI text-embedding-3-small, 256 for the deterministic
    # fallback used in tests / when no API key is configured).
    embedding = models.JSONField(default=list)
    embedding_model = models.CharField(max_length=100, blank=True)
    embedding_dim = models.IntegerField(default=0)
    # Optional structural tag (heading text, section type, etc.) so the
    # retriever can show a human-readable snippet header.
    section_label = models.CharField(max_length=200, blank=True)
    token_count = models.IntegerField(default=0)

    class Meta:
        db_table = "rag_knowledge_chunk"
        ordering = ["source", "chunk_index"]
        indexes = [
            models.Index(fields=["user", "website"], name="rag_kn_chk_user_website_idx"),
            models.Index(fields=["source", "chunk_index"], name="rag_kn_chk_source_idx_idx"),
        ]

    def __str__(self):
        preview = (self.text or "")[:60].replace("\n", " ")
        return f"KnowledgeChunk({self.source_id}#{self.chunk_index}: {preview})"
