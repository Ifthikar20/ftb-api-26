"""
Hardened Stripe webhook handler.

Security features:
    1. Signature verification (Stripe-Signature header)
    2. Idempotency via BillingEvent deduplication
    3. Replay attack protection (reject events > 5 min old)
    4. Database transaction with select_for_update on subscription writes
    5. Structured error handling: 200 for business errors, 500 for transient
    6. Full audit trail via BillingEvent model
"""

import logging
import time

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.billing.models import BillingEvent
from apps.billing.services.stripe_service import StripeService
from core.logging.audit_logger import audit_log

logger = logging.getLogger("billing")

# Maximum age of an event before we reject it (replay protection)
MAX_EVENT_AGE_SECONDS = 300  # 5 minutes


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events with production-grade hardening.

    Flow:
        1. Verify signature
        2. Check event age (replay protection)
        3. Check idempotency (BillingEvent dedup)
        4. Process event in atomic transaction
        5. Record result in BillingEvent
    """
    start_time = time.time()

    # ── 1. Verify signature ──
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        logger.warning("Webhook received without Stripe-Signature header.")
        return HttpResponse(status=400)

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured — cannot verify webhooks.")
        return HttpResponse(status=500)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        logger.error("Invalid Stripe webhook payload.")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature — possible tampering.")
        return HttpResponse(status=400)

    event_id = event["id"]
    event_type = event["type"]
    event_created = event.get("created", 0)  # Unix timestamp

    # ── 2. Replay protection ──
    if event_created:
        event_age = time.time() - event_created
        if event_age > MAX_EVENT_AGE_SECONDS:
            logger.warning(
                f"Rejecting stale webhook event {event_id} "
                f"(age={event_age:.0f}s, max={MAX_EVENT_AGE_SECONDS}s)"
            )
            return JsonResponse(
                {"status": "rejected", "reason": "event_too_old"},
                status=200,  # Don't trigger Stripe retries for this
            )

    # ── 3. Idempotency check ──
    try:
        billing_event = BillingEvent.objects.create(
            stripe_event_id=event_id,
            event_type=event_type,
            payload=event.get("data", {}),
        )
    except IntegrityError:
        # Already processed this event — idempotent skip
        logger.info(f"Duplicate webhook event skipped: {event_id} ({event_type})")
        return JsonResponse({"status": "duplicate", "event_id": event_id}, status=200)

    # ── 4. Process event ──
    data = event["data"]["object"]

    logger.info(f"Processing webhook: {event_type} (event_id={event_id})")

    try:
        with transaction.atomic():
            _dispatch_event(event_type, data)

        # Mark as processed
        processing_time_ms = int((time.time() - start_time) * 1000)
        billing_event.processed = True
        billing_event.processing_time_ms = processing_time_ms
        billing_event.save(update_fields=["processed", "processing_time_ms"])

        logger.info(
            f"Webhook processed: {event_type} in {processing_time_ms}ms "
            f"(event_id={event_id})"
        )

        # Compliance: audit log every successful webhook
        audit_log(
            "billing.webhook_processed",
            action="webhook",
            resource_type="billing_event",
            resource_id=event_id,
            metadata={"event_type": event_type, "processing_time_ms": processing_time_ms},
            success=True,
        )

        return JsonResponse(
            {"status": "processed", "event_id": event_id, "time_ms": processing_time_ms},
            status=200,
        )

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        error_msg = f"{type(e).__name__}: {e}"

        billing_event.processed = False
        billing_event.processing_error = error_msg
        billing_event.processing_time_ms = processing_time_ms
        billing_event.save(update_fields=["processed", "processing_error", "processing_time_ms"])

        logger.error(
            f"Webhook handler error for {event_type}: {error_msg}",
            exc_info=True,
            extra={"event_id": event_id, "event_type": event_type},
        )

        # Compliance: audit log failed webhooks
        audit_log(
            "billing.webhook_failed",
            action="webhook",
            resource_type="billing_event",
            resource_id=event_id,
            metadata={"event_type": event_type},
            success=False,
            error_message=error_msg,
            level="error",
        )

        # Distinguish transient vs permanent errors:
        # - Database errors → 500 (Stripe will retry)
        # - Application logic errors → 200 (don't retry, it'll fail again)
        from django.db import OperationalError, DatabaseError
        if isinstance(e, (OperationalError, DatabaseError)):
            return HttpResponse(status=500)

        # Business logic error — return 200 so Stripe doesn't retry
        return JsonResponse(
            {"status": "error", "event_id": event_id, "error": error_msg},
            status=200,
        )


def _dispatch_event(event_type: str, data: dict) -> None:
    """Route event to the correct handler."""
    handlers = {
        "checkout.session.completed": StripeService.handle_checkout_completed,
        "customer.subscription.updated": StripeService.handle_subscription_updated,
        "customer.subscription.deleted": StripeService.handle_subscription_updated,
        "invoice.paid": StripeService.handle_invoice_paid,
        "invoice.payment_failed": StripeService.handle_invoice_payment_failed,
        "customer.subscription.trial_will_end": _handle_trial_ending,
    }

    handler = handlers.get(event_type)
    if handler:
        if event_type in ("checkout.session.completed",):
            handler(session=data)
        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            handler(stripe_subscription=data)
        elif event_type.startswith("invoice."):
            handler(invoice=data)
        else:
            handler(data=data)
    else:
        logger.debug(f"Unhandled Stripe event type: {event_type}")


def _handle_trial_ending(*, data: dict) -> None:
    """Log trial ending — extend with email notification if needed."""
    sub_id = data.get("id", "unknown")
    logger.info(f"Trial ending soon for subscription: {sub_id}")
