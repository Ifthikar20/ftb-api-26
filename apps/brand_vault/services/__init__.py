"""Public service API for the brand_vault app."""
from apps.brand_vault.services.embeddings import cosine_similarity, embed_text
from apps.brand_vault.services.fact_extractor import (
    extract_facts_for_chunk,
    extract_facts_for_website,
    persist_extracted_items,
)
from apps.brand_vault.services.fact_versioning import (
    approve_fact,
    record_creation,
    reject_fact,
    supersede_fact,
)
from apps.brand_vault.services.tone_sampler import sample_tone_from_chunks

__all__ = [
    "cosine_similarity",
    "embed_text",
    "extract_facts_for_chunk",
    "extract_facts_for_website",
    "persist_extracted_items",
    "approve_fact",
    "record_creation",
    "reject_fact",
    "supersede_fact",
    "sample_tone_from_chunks",
]
