import logging
from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.billing.tasks.sync_subscription_statuses")
def sync_subscription_statuses():
    """
    Sync all active subscriptions with Stripe.
    Run daily via Celery Beat to catch any missed webhooks.
    """
    from apps.billing.models import Subscription
    from apps.billing.services.stripe_service import StripeService

    active_subs = Subscription.objects.filter(
        status__in=["active", "trialing", "past_due"],
        stripe_subscription_id__isnull=False,
    ).exclude(stripe_subscription_id="").select_related("user")

    synced = 0
    errors = 0

    for sub in active_subs:
        try:
            StripeService.sync_subscription(user=sub.user)
            synced += 1
        except Exception as e:
            errors += 1
            logger.error(f"Sync failed for user {sub.user.email}: {e}")

    logger.info(f"Subscription sync complete: {synced} synced, {errors} errors")


@shared_task(name="apps.billing.tasks.check_past_due_subscriptions")
def check_past_due_subscriptions():
    """
    Downgrade users with past_due subscriptions older than 7 days.
    Gives users a grace period before feature restriction.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.billing.models import Subscription

    cutoff = timezone.now() - timedelta(days=7)
    past_due = Subscription.objects.filter(
        status="past_due",
        updated_at__lt=cutoff,
    ).select_related("user")

    for sub in past_due:
        sub.user.plan = "starter"
        sub.user.save(update_fields=["plan"])
        sub.plan = "starter"
        sub.status = "canceled"
        sub.save(update_fields=["plan", "status"])
        logger.warning(f"Downgraded past-due user: {sub.user.email}")
