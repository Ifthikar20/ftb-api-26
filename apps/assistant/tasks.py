"""Celery wrappers for the Phase 2 knowledge producers.

Each task is a one-line wrapper so the adapter stays synchronously
callable from tests and the backfill command (no Celery worker runs in
local dev). Every task is best-effort: a failure must never break the
audit or agent flow that dispatched it.
"""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.assistant.tasks.ingest_audit_knowledge")
def ingest_audit_knowledge(audit_id: str) -> int:
    """Mirror one completed audit's answers + the website's citations."""
    from apps.assistant.services import producers

    try:
        written = producers.ingest_audit_responses(audit_id)
        from apps.llm_ranking.models import LLMRankingAudit

        audit = LLMRankingAudit.objects.filter(id=audit_id).only("website_id").first()
        if audit is not None and audit.website_id:
            written += producers.ingest_citation_domains(audit.website_id)
            written += producers.ingest_saved_prompts(audit.website_id)
        return written
    except Exception as exc:
        logger.warning("assistant audit ingest failed for %s: %s", audit_id, exc)
        return 0


@shared_task(name="apps.assistant.tasks.sweep_security_alerts")
def sweep_security_alerts() -> int:
    """Periodic sweep: mirror open security findings for active websites."""
    from apps.assistant.services import producers
    from apps.websites.models import Website

    total = 0
    for website_id in (
        Website.objects.filter(is_active=True).values_list("id", flat=True)
    ):
        try:
            total += producers.ingest_security_alerts(website_id)
        except Exception as exc:
            logger.warning("alert ingest failed for website %s: %s", website_id, exc)
    return total
