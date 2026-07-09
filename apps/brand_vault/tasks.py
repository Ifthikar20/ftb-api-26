"""Celery tasks for the brand_vault app."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.brand_vault.tasks.extract_facts_for_website")
def extract_facts_for_website(website_id: str, limit: int = 50) -> int:
    from apps.brand_vault.services.fact_extractor import extract_facts_for_website as _impl
    try:
        result = _impl(website_id, limit=limit)
    except Exception as exc:  # pragma: no cover
        logger.exception("brand_vault.extract_facts_for_website(%s) failed: %s", website_id, exc)
        return 0
    # Chain tone sampling so Phase 4's voice guard has fresh exemplars.
    try:
        sample_tone_for_website.delay(website_id)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not queue sample_tone_for_website(%s): %s", website_id, exc)
    return result


@shared_task(name="apps.brand_vault.tasks.sample_tone_for_website")
def sample_tone_for_website(website_id: str, target_count: int = 30) -> int:
    """Run the tone sampler for a website. Returns new sample count."""
    from apps.brand_vault.services.tone_sampler import sample_tone_from_chunks
    try:
        return sample_tone_from_chunks(website_id, target_count=target_count)
    except Exception as exc:  # pragma: no cover
        logger.exception("brand_vault.sample_tone_for_website(%s) failed: %s", website_id, exc)
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


# ── Brand Security ────────────────────────────────────────────────────────

@shared_task(name="apps.brand_vault.tasks.run_security_agent")
def run_security_agent(website_id: str, agent_id: str) -> dict:
    """Run one Brand Security agent for one website."""
    from apps.brand_vault.services.security.orchestrator import run_agent
    from apps.websites.models import Website

    try:
        website = Website.objects.get(pk=website_id)
    except Website.DoesNotExist:
        return {"agent_id": agent_id, "error": "website_not_found"}
    try:
        return run_agent(website, agent_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("run_security_agent(%s,%s) failed: %s", website_id, agent_id, exc)
        return {"agent_id": agent_id, "error": str(exc)[:200]}


@shared_task(name="apps.brand_vault.tasks.run_security_scan")
def run_security_scan(website_id: str, only: list[str] | None = None) -> dict:
    """Run every enabled Brand Security agent for one website."""
    from apps.brand_vault.services.security.orchestrator import run_all_agents
    from apps.websites.models import Website

    try:
        website = Website.objects.get(pk=website_id)
    except Website.DoesNotExist:
        return {"error": "website_not_found"}
    try:
        return run_all_agents(website, only=only)
    except Exception as exc:  # pragma: no cover
        logger.exception("run_security_scan(%s) failed: %s", website_id, exc)
        return {"error": str(exc)[:200]}


@shared_task(name="apps.brand_vault.tasks.dispatch_scheduled_security_agents")
def dispatch_scheduled_security_agents() -> int:
    """Beat entry — fires any agent whose ``next_run_at`` is due.

    We deliberately dispatch per (website, agent) so an unhealthy agent
    can't block the rest of a scan run.
    """
    from django.utils import timezone

    from apps.brand_vault.models import BrandSecurityAgent

    now = timezone.now()
    due = BrandSecurityAgent.objects.filter(
        enabled=True,
        next_run_at__lte=now,
    ).exclude(
        schedule=BrandSecurityAgent.SCHEDULE_MANUAL,
    ).values("website_id", "agent_id")

    dispatched = 0
    for row in due:
        try:
            run_security_agent.delay(str(row["website_id"]), row["agent_id"])
            dispatched += 1
        except Exception as exc:  # pragma: no cover
            logger.warning("dispatch_scheduled_security_agents queue failed: %s", exc)
    return dispatched
