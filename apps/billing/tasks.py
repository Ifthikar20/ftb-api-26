import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.billing.tasks.sync_subscription_statuses")
def sync_subscription_statuses():
    """Sync subscription statuses from Stripe."""
    logger.info("Subscription sync task running.")
