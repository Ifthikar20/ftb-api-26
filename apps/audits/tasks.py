import logging
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=240,
    time_limit=300,
    acks_late=True,
    reject_on_worker_lost=True,
    name="apps.audits.tasks.run_website_audit",
)
def run_website_audit(self, website_id: str, audit_id: str):
    """Execute a full website audit asynchronously."""
    from django.utils import timezone
    from apps.audits.models import Audit
    from apps.audits.services.audit_orchestrator import AuditOrchestrator

    try:
        audit = Audit.objects.get(id=audit_id, status="pending")
        audit.status = "running"
        audit.save(update_fields=["status"])

        result = AuditOrchestrator.execute(website_id=website_id, audit=audit)

        # Run SEO Grader for per-page analysis
        try:
            from apps.audits.services.seo_grader import SEOGrader
            from apps.websites.models import Website
            website = Website.objects.get(id=website_id)
            SEOGrader.run(website=website, audit=audit)
        except Exception as grader_exc:
            logger.warning(f"SEO Grader failed for {website_id}: {grader_exc}")

        audit.status = "completed"
        audit.completed_at = timezone.now()
        audit.overall_score = result["overall_score"]
        audit.seo_score = result["seo_score"]
        audit.performance_score = result["performance_score"]
        audit.mobile_score = result.get("mobile_score")
        audit.security_score = result.get("security_score")
        audit.content_score = result.get("content_score")
        audit.save()

        logger.info(f"Audit completed for website {website_id}, score: {result['overall_score']}")

    except Exception as exc:
        logger.error(f"Audit failed for {website_id}: {exc}")
        try:
            audit = Audit.objects.get(id=audit_id)
            audit.status = "failed"
            audit.save(update_fields=["status"])
        except Exception:
            pass
        raise self.retry(exc=exc)


@shared_task(name="apps.audits.tasks.run_scheduled_audits")
def run_scheduled_audits():
    """Run audits for all websites with active schedules."""
    from apps.audits.models import AuditSchedule, Audit

    for schedule in AuditSchedule.objects.filter(is_active=True):
        if not Audit.objects.filter(
            website=schedule.website, status__in=["pending", "running"]
        ).exists():
            audit = Audit.objects.create(website=schedule.website)
            run_website_audit.delay(str(schedule.website.id), str(audit.id))
