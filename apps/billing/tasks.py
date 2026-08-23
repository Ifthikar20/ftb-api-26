"""Billing maintenance tasks.

Subscription lifecycle (renewals, dunning, grace periods, revocation) is
handled by Polar and mirrored locally via webhooks / checkout
confirmation (apps.billing.services.polar_billing). The only recurring
job left on our side is pruning the webhook idempotency ledger.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("billing")

# BillingEvent rows older than this are pruned. 90 days keeps a useful
# audit window without unbounded growth.
EVENT_RETENTION_DAYS = 90


@shared_task(name="apps.billing.tasks.cleanup_stale_events")
def cleanup_stale_events():
    """Delete processed webhook events past the retention window."""
    from apps.billing.models import BillingEvent

    cutoff = timezone.now() - timedelta(days=EVENT_RETENTION_DAYS)
    deleted, _ = BillingEvent.objects.filter(
        processed=True, created_at__lt=cutoff
    ).delete()
    if deleted:
        logger.info("cleanup_stale_events: removed %d processed events", deleted)
    return {"deleted": deleted}
