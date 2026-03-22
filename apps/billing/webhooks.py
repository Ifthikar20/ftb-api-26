import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.billing.services.stripe_service import StripeService

logger = logging.getLogger("apps")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    Security: All events are verified via signature before processing.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        logger.warning("Stripe webhook received without signature header.")
        return HttpResponse(status=400)

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured.")
        return HttpResponse(status=500)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        logger.error("Invalid Stripe webhook payload.")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature — possible tampering.")
        return HttpResponse(status=400)

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Stripe webhook received: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            StripeService.handle_checkout_completed(session=data)

        elif event_type == "customer.subscription.updated":
            StripeService.handle_subscription_updated(stripe_subscription=data)

        elif event_type == "customer.subscription.deleted":
            StripeService.handle_subscription_updated(stripe_subscription=data)

        elif event_type == "invoice.paid":
            StripeService.handle_invoice_paid(invoice=data)

        elif event_type == "invoice.payment_failed":
            StripeService.handle_invoice_payment_failed(invoice=data)

        elif event_type == "customer.subscription.trial_will_end":
            logger.info(f"Trial ending soon for subscription: {data.get('id')}")

        else:
            logger.debug(f"Unhandled Stripe event: {event_type}")

    except Exception as e:
        logger.error(f"Webhook handler error for {event_type}: {e}", exc_info=True)
        # Return 200 anyway — Stripe retries on 5xx, and we don't want infinite retries
        # for application logic errors. The error is logged for debugging.

    return HttpResponse(status=200)
