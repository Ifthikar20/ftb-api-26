import logging
from datetime import timedelta

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


# ── Periodic scheduling ─────────────────────────────────────────────────────


FREQUENCY_DELTAS = {
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
}


@shared_task(name="apps.llm_ranking.tasks.dispatch_scheduled_audits")
def dispatch_scheduled_audits() -> None:
    """
    Celery Beat task: check all enabled LLMRankingSchedule records
    whose next_run_at has passed, create an audit, and advance the schedule.

    Runs every 15 minutes via beat_schedule.
    """
    from django.utils import timezone

    from apps.llm_ranking.models import LLMRankingAudit, LLMRankingSchedule
    from apps.llm_ranking.services.ranking_service import LLMRankingService

    now = timezone.now()
    due = LLMRankingSchedule.objects.filter(
        is_enabled=True,
        next_run_at__lte=now,
    ).select_related("website")

    for schedule in due:
        try:
            # Per-user monthly AI spend cap. The on-demand audit path enforces
            # this in the API view; scheduled runs would otherwise bypass it
            # and silently push the user over their cap. Skip and advance the
            # schedule so we re-check next cycle.
            cap_user = schedule.created_by
            cap = float(getattr(cap_user, "monthly_ai_cost_cap_usd", 0) or 0)
            if cap > 0:
                from core.ai_tracking import month_to_date_cost
                spent = month_to_date_cost(cap_user)
                if spent >= cap:
                    logger.warning(
                        "Skipping scheduled audit for %s: user %s at cap "
                        "($%.2f / $%.2f).",
                        schedule.website.name, cap_user.id, spent, cap,
                    )
                    # Advance next_run_at so we don't tight-loop checking it.
                    delta = FREQUENCY_DELTAS.get(schedule.frequency, timedelta(weeks=1))
                    schedule.next_run_at = now + delta
                    schedule.save(update_fields=["next_run_at", "updated_at"])
                    continue

            # Generate prompts for the scheduled audit
            prompts = LLMRankingService.generate_prompts(
                business_name=schedule.business_name,
                industry=schedule.industry,
                description=schedule.business_description,
                keywords=schedule.keywords,
                location=schedule.location,
                user=cap_user,
                website=schedule.website,
            )

            # Filter requested providers down to those that are both
            # implemented and configured. Mirrors the API path so a schedule
            # saved with stale provider keys cannot queue dead cells.
            from apps.llm_ranking.providers import PROVIDERS
            from django.conf import settings as _settings
            requested = schedule.providers or list(PROVIDERS.keys())
            selected_providers = [
                key for key in requested
                if key in PROVIDERS
                and getattr(_settings, PROVIDERS[key].api_key_setting, "")
            ] or ["claude"]

            audit = LLMRankingAudit.objects.create(
                website=schedule.website,
                created_by=schedule.created_by,
                business_name=schedule.business_name,
                business_description=schedule.business_description,
                industry=schedule.industry,
                location=schedule.location,
                keywords=schedule.keywords,
                prompts=prompts,
                providers_queried=selected_providers,
            )

            # Queue the audit execution
            run_llm_ranking_audit.delay(audit_id=str(audit.id))

            # Advance the schedule
            delta = FREQUENCY_DELTAS.get(schedule.frequency, timedelta(weeks=1))
            schedule.last_run_at = now
            schedule.next_run_at = now + delta
            schedule.save(update_fields=["last_run_at", "next_run_at", "updated_at"])

            logger.info(
                "Scheduled LLM audit created for %s (schedule=%s, next=%s)",
                schedule.website.name, schedule.id, schedule.next_run_at,
            )

        except Exception as exc:
            logger.error(
                "Failed to dispatch scheduled LLM audit for schedule %s: %s",
                schedule.id, exc,
            )
