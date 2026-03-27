"""
Billing Celery tasks — periodic maintenance and reconciliation.

Tasks:
    1. sync_subscription_statuses — daily Stripe reconciliation
    2. check_past_due_subscriptions — 7-day grace period downgrade
    3. cleanup_stale_events — purge BillingEvent records > 90 days
    4. reconcile_stripe_state — deep sync comparing DB vs Stripe
"""

import logging

from celery import shared_task

logger = logging.getLogger("billing")


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
    from datetime import timedelta

    from django.db import transaction
    from django.utils import timezone

    from apps.billing.models import Subscription

    cutoff = timezone.now() - timedelta(days=7)
    past_due = Subscription.objects.filter(
        status="past_due",
        updated_at__lt=cutoff,
    ).select_related("user")

    downgraded = 0
    for sub in past_due:
        with transaction.atomic():
            # Lock the subscription row
            sub = Subscription.objects.select_for_update().get(pk=sub.pk)
            if sub.status != "past_due":
                continue  # Status changed since our query

            sub.user.plan = "individual"
            sub.user.save(update_fields=["plan"])
            sub.plan = "individual"
            sub.status = "canceled"
            sub.save(update_fields=["plan", "status"])
            downgraded += 1
            logger.warning(f"Downgraded past-due user: {sub.user.email}")

    logger.info(f"Past-due check complete: {downgraded} users downgraded")


@shared_task(name="apps.billing.tasks.cleanup_stale_events")
def cleanup_stale_events():
    """
    Purge BillingEvent records older than 90 days.
    Keeps the billing_event table from growing unbounded.
    Run weekly via Celery Beat.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.billing.models import BillingEvent

    cutoff = timezone.now() - timedelta(days=90)
    deleted_count, _ = BillingEvent.objects.filter(
        created_at__lt=cutoff,
        processed=True,
    ).delete()

    logger.info(f"Cleaned up {deleted_count} stale billing events (>90 days)")


@shared_task(name="apps.billing.tasks.reconcile_stripe_state")
def reconcile_stripe_state():
    """
    Deep reconciliation: compare every active subscription in our DB
    against the actual state in Stripe.

    Catches:
        - Missed webhooks
        - State drift from manual Stripe Dashboard changes
        - Canceled subscriptions that we never got the webhook for

    Run daily, offset from sync_subscription_statuses.
    """
    from apps.billing.models import Subscription
    from apps.billing.services.circuit_breaker import stripe_circuit
    from apps.billing.services.stripe_service import StripeService

    # Don't run if Stripe is down
    if not stripe_circuit.is_available:
        logger.warning("Reconciliation skipped — circuit breaker is open")
        return

    active_subs = Subscription.objects.filter(
        stripe_subscription_id__isnull=False,
    ).exclude(stripe_subscription_id="").select_related("user")

    reconciled = 0
    mismatches = 0
    errors = 0

    for sub in active_subs:
        try:
            result = StripeService.sync_subscription(user=sub.user)
            sub.refresh_from_db()

            if result.get("status") != sub.status or result.get("plan") != sub.plan:
                mismatches += 1
                logger.warning(
                    f"State mismatch for {sub.user.email}: "
                    f"DB({sub.status}/{sub.plan}) vs Stripe({result})"
                )
            reconciled += 1
        except Exception as e:
            errors += 1
            logger.error(f"Reconciliation failed for {sub.user.email}: {e}")

    logger.info(
        f"Reconciliation complete: {reconciled} checked, "
        f"{mismatches} mismatches, {errors} errors"
    )
