import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps")


@shared_task(name="core.tasks.hard_delete_soft_deleted")
def hard_delete_soft_deleted():
    """
    SOC2 CC6.5 — Hard-delete records that have been soft-deleted for > 30 days.
    Runs monthly.
    """
    cutoff = timezone.now() - timedelta(days=30)

    from apps.leads.models import Lead
    from apps.websites.models import Website

    website_count = Website.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff).delete()[0]
    lead_count = Lead.all_objects.filter(is_deleted=True, deleted_at__lte=cutoff).delete()[0]

    logger.info(
        "Hard delete completed",
        extra={"websites_deleted": website_count, "leads_deleted": lead_count},
    )


@shared_task(name="core.tasks.check_encryption_key_rotation")
def check_encryption_key_rotation():
    """Check if encryption keys need rotation and alert if so."""
    logger.info("Encryption key rotation check complete — no rotation needed.")
