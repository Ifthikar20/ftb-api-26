"""
Ingest pipeline for the RAG knowledge base.

Given a (user, website, url) triple:

    1. Scrape the page (or crawl if requested).
    2. Hash the canonical content; skip if unchanged since last ingest.
    3. Chunk the text with the project chunker.
    4. Embed each chunk in a single batch call.
    5. Persist KnowledgeSource + KnowledgeChunk rows transactionally.

The pipeline is the only entrypoint that should be writing chunks —
keep ad-hoc creation out of views and tasks so the (user, website, url)
uniqueness invariant is respected.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.llm_ranking.services.domain_scanner import scan_domain
from apps.rag.models import KnowledgeChunk, KnowledgeSource
from apps.rag.services.chunker import chunk_text
from apps.rag.services.crawler import crawl_site
from apps.rag.services.embedder import embed_texts

logger = logging.getLogger("apps")


@dataclass
class IngestResult:
    source_id: str
    url: str
    status: str
    chunk_count: int
    skipped_unchanged: bool = False
    error: str | None = None


def _dispatch_auto_fact_extraction(website, kind: str) -> None:
    """Auto-extract brand facts after fresh chunks land.

    Debounced so a 12-page crawl triggers one extraction pass, not
    twelve: the first ingest in the window claims the cache flag
    (cache.add is atomic) and schedules extraction 120s out so the rest
    of the crawl's pages land first. audit_context is excluded — the
    learning loop must never mint facts from LLM-generated context.
    Extraction itself is idempotent (only chunks without facts are read),
    so overlapping dispatches are harmless.
    """
    try:
        from django.conf import settings

        if not getattr(settings, "BRAND_VAULT_EXTRACTION_ENABLED", True):
            return
        if kind == KnowledgeSource.KIND_AUDIT_CONTEXT:
            return
        from django.core.cache import cache

        if cache.add(f"bv:auto_extract:{website.id}", 1, timeout=180):
            from apps.brand_vault.tasks import extract_facts_for_website

            extract_facts_for_website.apply_async(
                args=[str(website.id)], countdown=120,
            )
    except Exception as exc:  # pragma: no cover — never block an ingest
        logger.debug("auto fact-extraction dispatch skipped: %s", exc)


def ingest_url(
    *,
    user,
    website,
    url: str,
    kind: str = KnowledgeSource.KIND_OTHER,
    title: str = "",
    text: str | None = None,
    source_app: str | None = None,
    source_ref: str | None = None,
    metadata: dict | None = None,
    recorded_at: datetime | None = None,
) -> IngestResult:
    """
    Ingest a single URL. If ``text`` is supplied (e.g. from an audit's
    enrichment step), we use it directly rather than re-fetching the page.

    Provenance passthrough (all optional; defaults preserve the original
    brand-input behavior): ``source_app``/``source_ref`` land on the
    KnowledgeSource, ``metadata``/``recorded_at`` land on every chunk
    written this pass. Source adapters use these so retrieval can filter
    by producing app and weight by content time.
    """
    defaults = {
        "kind": kind, "title": title or "",
        "status": KnowledgeSource.STATUS_PENDING,
    }
    if source_app:
        defaults["source_app"] = source_app
    if source_ref:
        defaults["source_ref"] = source_ref
    source, created = KnowledgeSource.objects.get_or_create(
        user=user, website=website, url=url, defaults=defaults,
    )
    if not created and kind and source.kind != kind:
        # Allow upgrading kind when a more specific tag is supplied.
        source.kind = kind
    if not created and source_app and source.source_app != source_app:
        source.source_app = source_app
    if not created and source_ref and source.source_ref != source_ref:
        source.source_ref = source_ref

    source.status = KnowledgeSource.STATUS_INGESTING
    source.error_message = ""
    source.save(update_fields=[
        "status", "kind", "source_app", "source_ref",
        "error_message", "updated_at",
    ])

    try:
        if text is None:
            scan = scan_domain(url)
            if not scan.get("success"):
                raise RuntimeError(scan.get("error") or "scan failed")
            page_text = scan.get("content_summary") or ""
            page_title = scan.get("business_name") or title or ""
        else:
            page_text = text
            page_title = title

        if not page_text.strip():
            raise RuntimeError("no text extracted")

        digest = hashlib.sha256(page_text.encode("utf-8")).hexdigest()
        if source.content_hash == digest and source.chunk_count > 0:
            source.status = KnowledgeSource.STATUS_READY
            source.last_ingested_at = timezone.now()
            source.save(update_fields=["status", "last_ingested_at", "updated_at"])
            return IngestResult(
                source_id=str(source.id), url=url,
                status=source.status, chunk_count=source.chunk_count,
                skipped_unchanged=True,
            )

        chunks = chunk_text(page_text, default_label=page_title or url)
        if not chunks:
            raise RuntimeError("no chunks produced")

        vectors, model, dim = embed_texts(
            [c.text for c in chunks],
            user=user, website=website,
            metadata={"source_id": str(source.id)},
        )
        if len(vectors) != len(chunks):
            raise RuntimeError("embedding count mismatch")

        with transaction.atomic():
            KnowledgeChunk.objects.filter(source=source).delete()
            KnowledgeChunk.objects.bulk_create([
                KnowledgeChunk(
                    source=source, user=user, website=website,
                    chunk_index=i, text=c.text,
                    embedding=vectors[i], embedding_model=model,
                    embedding_dim=dim, section_label=c.section_label,
                    token_count=c.token_count,
                    metadata=dict(metadata) if metadata else {},
                    recorded_at=recorded_at,
                )
                for i, c in enumerate(chunks)
            ])
            source.title = (page_title or source.title)[:500]
            source.content_hash = digest
            source.chunk_count = len(chunks)
            source.status = KnowledgeSource.STATUS_READY
            source.last_ingested_at = timezone.now()
            source.save(update_fields=[
                "title", "content_hash", "chunk_count", "status",
                "last_ingested_at", "updated_at",
            ])

        _dispatch_auto_fact_extraction(website, kind)

        return IngestResult(
            source_id=str(source.id), url=url,
            status=source.status, chunk_count=len(chunks),
        )

    except Exception as exc:
        logger.warning("RAG ingest failed for %s: %s", url, exc)
        source.status = KnowledgeSource.STATUS_FAILED
        source.error_message = str(exc)[:500]
        source.save(update_fields=["status", "error_message", "updated_at"])
        return IngestResult(
            source_id=str(source.id), url=url,
            status=source.status, chunk_count=0, error=str(exc)[:500],
        )


def ingest_site(
    *,
    user,
    website,
    seed_url: str,
    page_cap: int = 12,
    depth: int = 1,
) -> list[IngestResult]:
    """Crawl a site from ``seed_url`` and ingest each discovered page."""
    pages = crawl_site(seed_url, page_cap=page_cap, depth=depth)
    results: list[IngestResult] = []
    for page in pages:
        if not page.get("success"):
            continue
        results.append(ingest_url(
            user=user, website=website,
            url=page["url"],
            kind=page.get("kind") or KnowledgeSource.KIND_OTHER,
            title=page.get("business_name") or "",
            text=page.get("content_summary") or "",
        ))
    return results


def ingest_audit_context(
    *, user, website, audit_id: str, llm_context: str,
) -> IngestResult | None:
    """
    Persist the enriched system-prompt context produced for an audit so
    the next audit's prompts can draw on it. The "learning" loop.
    """
    if not llm_context.strip():
        return None
    pseudo_url = f"audit://{audit_id}"
    return ingest_url(
        user=user, website=website,
        url=pseudo_url,
        kind=KnowledgeSource.KIND_AUDIT_CONTEXT,
        title=f"Audit context {audit_id}",
        text=llm_context,
    )
