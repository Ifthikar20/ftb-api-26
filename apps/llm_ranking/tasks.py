import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.llm_ranking.tasks.run_llm_ranking_audit", bind=True, max_retries=1)
def run_llm_ranking_audit(self, *, audit_id: str) -> None:
    """Run a full LLM ranking audit asynchronously."""
    from apps.llm_ranking.models import LLMRankingAudit
    from apps.llm_ranking.services.ranking_service import LLMRankingService

    try:
        LLMRankingService.run_audit(audit_id=audit_id)
    except Exception as exc:
        logger.error("LLM ranking audit %s failed: %s", audit_id, exc)
        try:
            LLMRankingAudit.objects.filter(id=audit_id).update(
                status=LLMRankingAudit.STATUS_FAILED,
                error_message=str(exc),
            )
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30) from None
