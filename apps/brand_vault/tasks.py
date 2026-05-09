"""Celery tasks for the brand_vault app."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.brand_vault.tasks.extract_facts_for_website")
def extract_facts_for_website(website_id: str, limit: int = 50) -> int:
    from apps.brand_vault.services.fact_extractor import extract_facts_for_website as _impl
    try:
        return _impl(website_id, limit=limit)
    except Exception as exc:  # pragma: no cover
        logger.exception("brand_vault.extract_facts_for_website(%s) failed: %s", website_id, exc)
        return 0


@shared_task(name="apps.brand_vault.tasks.refresh_fact_embeddings")
def refresh_fact_embeddings() -> int:
    """Re-embed any BrandFact missing an embedding. Daily cron."""
    from apps.brand_vault.models import BrandFact
    from apps.brand_vault.services.embeddings import embed_text

    qs = BrandFact.objects.filter(embedding__isnull=True)
    count = 0
    for fact in qs.iterator(chunk_size=200):
        try:
            fact.embedding = embed_text(f"{fact.subject} {fact.predicate} {fact.object}")
            fact.save(update_fields=["embedding", "updated_at"])
            count += 1
        except Exception as exc:  # pragma: no cover
            logger.warning("refresh_fact_embeddings(%s) failed: %s", fact.id, exc)
    return count
