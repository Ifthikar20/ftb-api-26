import json
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
    """Handle Stripe webhook events (signed for security)."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid Stripe webhook payload.")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe webhook signature.")
        return HttpResponse(status=400)

    try:
        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            StripeService.handle_checkout_completed(session=data)
        elif event_type == "customer.subscription.updated":
            StripeService.handle_subscription_updated(stripe_subscription=data)
        elif event_type == "customer.subscription.deleted":
            StripeService.handle_subscription_updated(stripe_subscription=data)
        elif event_type == "invoice.paid":
            logger.info(f"Invoice paid: {data.get('id')}")
        elif event_type == "invoice.payment_failed":
            logger.warning(f"Invoice payment failed: {data.get('id')}")

    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)
