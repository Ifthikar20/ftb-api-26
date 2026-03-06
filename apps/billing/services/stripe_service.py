import logging
from django.conf import settings

import stripe

from apps.billing.models import Subscription
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

PLAN_PRICE_IDS = {
    "starter": settings.STRIPE_STARTER_PRICE_ID if hasattr(settings, "STRIPE_STARTER_PRICE_ID") else "",
    "growth": settings.STRIPE_GROWTH_PRICE_ID if hasattr(settings, "STRIPE_GROWTH_PRICE_ID") else "",
    "scale": settings.STRIPE_SCALE_PRICE_ID if hasattr(settings, "STRIPE_SCALE_PRICE_ID") else "",
}


class StripeService:
    @staticmethod
    def get_or_create_customer(*, user) -> str:
        """Get or create a Stripe customer for this user."""
        stripe.api_key = settings.STRIPE_SECRET_KEY

        subscription, _ = Subscription.objects.get_or_create(user=user)

        if subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)},
        )

        subscription.stripe_customer_id = customer.id
        subscription.save(update_fields=["stripe_customer_id"])

        return customer.id

    @staticmethod
    def create_checkout_session(*, user, plan: str, success_url: str, cancel_url: str) -> str:
        """Create a Stripe checkout session URL."""
        stripe.api_key = settings.STRIPE_SECRET_KEY
        customer_id = StripeService.get_or_create_customer(user=user)
        price_id = PLAN_PRICE_IDS.get(plan, "")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id), "plan": plan},
        )

        audit_log("billing.checkout_created", user=user, metadata={"plan": plan})
        return session.url

    @staticmethod
    def create_portal_session(*, user, return_url: str) -> str:
        """Create a Stripe customer portal URL for managing subscription."""
        stripe.api_key = settings.STRIPE_SECRET_KEY
        customer_id = StripeService.get_or_create_customer(user=user)

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    @staticmethod
    def handle_subscription_updated(*, stripe_subscription: dict) -> None:
        """Handle subscription.updated webhook."""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription["id"]
            )
            subscription.status = stripe_subscription["status"]
            subscription.save(update_fields=["status"])
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found: {stripe_subscription['id']}")

    @staticmethod
    def handle_checkout_completed(*, session: dict) -> None:
        """Handle checkout.session.completed webhook — activate subscription."""
        from django.utils import timezone
        import datetime

        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan", "starter")

        if not user_id:
            return

        try:
            from apps.accounts.models import User
            user = User.objects.get(id=user_id)
            subscription, _ = Subscription.objects.get_or_create(user=user)
            subscription.plan = plan
            subscription.status = "active"
            subscription.stripe_subscription_id = session.get("subscription")
            subscription.save()
            user.plan = plan
            user.save(update_fields=["plan"])
            audit_log("billing.subscription_activated", user=user, metadata={"plan": plan})
        except Exception as e:
            logger.error(f"Checkout completion handler failed: {e}")
