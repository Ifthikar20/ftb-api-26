"""Public service API for the rag app."""
from apps.rag.services.chunker import Chunk, chunk_text
from apps.rag.services.crawler import (
    crawl_site,
    discover_from_sitemap,
    extract_same_domain_links,
)
from apps.rag.services.embedder import cosine_similarity, embed_one, embed_texts
from apps.rag.services.ingest_service import (
    IngestResult,
    ingest_audit_context,
    ingest_site,
    ingest_url,
)
from apps.rag.services.retriever import Hit, retrieve, retrieve_context_block

__all__ = [
    "Chunk",
    "chunk_text",
    "crawl_site",
    "discover_from_sitemap",
    "extract_same_domain_links",
    "cosine_similarity",
    "embed_one",
    "embed_texts",
    "IngestResult",
    "ingest_audit_context",
    "ingest_site",
    "ingest_url",
    "Hit",
    "retrieve",
    "retrieve_context_block",
]
