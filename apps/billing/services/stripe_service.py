import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

import stripe

from apps.billing.models import Subscription, Invoice
from core.logging.audit_logger import audit_log
from core.exceptions import GrowthPilotException

logger = logging.getLogger("apps")

# ── Stripe Price IDs — set via env vars; empty until keys are added ──
PLAN_PRICE_IDS = {
    "starter": getattr(settings, "STRIPE_STARTER_PRICE_ID", ""),
    "growth": getattr(settings, "STRIPE_GROWTH_PRICE_ID", ""),
    "scale": getattr(settings, "STRIPE_SCALE_PRICE_ID", ""),
}

PLAN_PRICE_IDS_ANNUAL = {
    "starter": getattr(settings, "STRIPE_STARTER_ANNUAL_PRICE_ID", ""),
    "growth": getattr(settings, "STRIPE_GROWTH_ANNUAL_PRICE_ID", ""),
    "scale": getattr(settings, "STRIPE_SCALE_ANNUAL_PRICE_ID", ""),
}

# Plan limits used for enforcement
PLAN_LIMITS = {
    "starter": {"websites": 1, "pageviews": 10000, "competitors": 3, "team_members": 1},
    "growth": {"websites": 5, "pageviews": -1, "competitors": 10, "team_members": 5},
    "scale": {"websites": -1, "pageviews": -1, "competitors": 50, "team_members": -1},
}


def _init_stripe():
    """Set the Stripe API key. Called at the top of every service method."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not stripe.api_key:
        raise GrowthPilotException(
            "Billing is not configured yet. Please try again later.",
            code="billing_not_configured",
            status_code=503,
        )


class StripeService:
    # ──────────────────────────────────
    #  Customer Management
    # ──────────────────────────────────

    @staticmethod
    def get_or_create_customer(*, user) -> str:
        """Get or create a Stripe customer for this user."""
        _init_stripe()
        subscription, _ = Subscription.objects.get_or_create(user=user)

        if subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=getattr(user, "full_name", user.email),
            metadata={"user_id": str(user.id)},
        )

        subscription.stripe_customer_id = customer.id
        subscription.save(update_fields=["stripe_customer_id"])
        audit_log("billing.customer_created", user=user, metadata={"customer_id": customer.id})
        return customer.id

    # ──────────────────────────────────
    #  Checkout Session
    # ──────────────────────────────────

    @staticmethod
    def create_checkout_session(*, user, plan: str, annual: bool = False,
                                 success_url: str, cancel_url: str) -> str:
        """Create a Stripe checkout session URL for subscribing."""
        _init_stripe()
        customer_id = StripeService.get_or_create_customer(user=user)

        price_map = PLAN_PRICE_IDS_ANNUAL if annual else PLAN_PRICE_IDS
        price_id = price_map.get(plan, "")

        if not price_id:
            raise GrowthPilotException(
                "This plan is not available for checkout yet.",
                code="plan_not_available",
                status_code=400,
            )

        # Prevent starting checkout if already on an active subscription
        try:
            existing = user.subscription
            if existing.status == "active" and existing.stripe_subscription_id:
                raise GrowthPilotException(
                    "You already have an active subscription. Use 'Manage Subscription' to change your plan.",
                    code="already_subscribed",
                    status_code=400,
                )
        except Subscription.DoesNotExist:
            pass

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id), "plan": plan, "annual": str(annual)},
            subscription_data={"metadata": {"user_id": str(user.id), "plan": plan}},
            allow_promotion_codes=True,
        )

        audit_log("billing.checkout_created", user=user, metadata={"plan": plan, "annual": annual})
        return session.url

    # ──────────────────────────────────
    #  Customer Portal (Manage / Cancel)
    # ──────────────────────────────────

    @staticmethod
    def create_portal_session(*, user, return_url: str) -> str:
        """Create a Stripe customer portal URL for managing subscription."""
        _init_stripe()
        customer_id = StripeService.get_or_create_customer(user=user)

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        audit_log("billing.portal_opened", user=user)
        return session.url

    # ──────────────────────────────────
    #  Webhook Handlers
    # ──────────────────────────────────

    @staticmethod
    def handle_checkout_completed(*, session: dict) -> None:
        """Handle checkout.session.completed webhook — activate subscription."""
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan", "starter")

        if not user_id:
            logger.warning("Checkout completed but no user_id in metadata.")
            return

        try:
            from apps.accounts.models import User
            user = User.objects.get(id=user_id)
            subscription, _ = Subscription.objects.get_or_create(user=user)
            subscription.plan = plan
            subscription.status = "active"
            subscription.stripe_subscription_id = session.get("subscription")
            subscription.stripe_customer_id = session.get("customer", subscription.stripe_customer_id)
            subscription.save()

            user.plan = plan
            user.save(update_fields=["plan"])

            audit_log("billing.subscription_activated", user=user, metadata={"plan": plan})
            logger.info(f"Subscription activated: user={user.email}, plan={plan}")

        except Exception as e:
            logger.error(f"Checkout completion handler failed: {e}", exc_info=True)

    @staticmethod
    def handle_subscription_updated(*, stripe_subscription: dict) -> None:
        """Handle subscription.updated and subscription.deleted webhooks."""
        sub_id = stripe_subscription.get("id")
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=sub_id)
            old_status = subscription.status
            new_status = stripe_subscription.get("status", old_status)

            subscription.status = new_status
            subscription.cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)

            # Update period dates
            period = stripe_subscription.get("current_period_start")
            if period:
                subscription.current_period_start = timezone.make_aware(
                    datetime.fromtimestamp(period)
                ) if isinstance(period, (int, float)) else period

            period_end = stripe_subscription.get("current_period_end")
            if period_end:
                subscription.current_period_end = timezone.make_aware(
                    datetime.fromtimestamp(period_end)
                ) if isinstance(period_end, (int, float)) else period_end

            # Update plan if items contain a known price
            items = stripe_subscription.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                for plan_name, pid in {**PLAN_PRICE_IDS, **PLAN_PRICE_IDS_ANNUAL}.items():
                    if pid and pid == price_id:
                        subscription.plan = plan_name
                        subscription.user.plan = plan_name
                        subscription.user.save(update_fields=["plan"])
                        break

            subscription.save()

            # If canceled, update user's plan to starter
            if new_status == "canceled" and old_status != "canceled":
                subscription.user.plan = "starter"
                subscription.user.save(update_fields=["plan"])
                audit_log("billing.subscription_canceled", user=subscription.user)
                logger.info(f"Subscription canceled: user={subscription.user.email}")

            logger.info(f"Subscription updated: {sub_id}, status={new_status}")

        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found for update: {sub_id}")

    @staticmethod
    def handle_invoice_paid(*, invoice: dict) -> None:
        """Handle invoice.paid webhook — store invoice record."""
        sub_id = invoice.get("subscription")
        if not sub_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_subscription_id=sub_id)
            Invoice.objects.update_or_create(
                stripe_invoice_id=invoice["id"],
                defaults={
                    "subscription": subscription,
                    "amount_paid": invoice.get("amount_paid", 0),
                    "currency": invoice.get("currency", "usd"),
                    "status": "paid",
                    "invoice_pdf": invoice.get("invoice_pdf", ""),
                    "period_start": timezone.make_aware(
                        datetime.fromtimestamp(invoice["period_start"])
                    ) if invoice.get("period_start") else None,
                    "period_end": timezone.make_aware(
                        datetime.fromtimestamp(invoice["period_end"])
                    ) if invoice.get("period_end") else None,
                },
            )
            logger.info(f"Invoice recorded: {invoice['id']}, amount=${invoice.get('amount_paid', 0) / 100:.2f}")

        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for invoice: {sub_id}")

    @staticmethod
    def handle_invoice_payment_failed(*, invoice: dict) -> None:
        """Handle invoice.payment_failed webhook — mark subscription as past_due."""
        sub_id = invoice.get("subscription")
        if not sub_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_subscription_id=sub_id)
            subscription.status = "past_due"
            subscription.save(update_fields=["status"])

            audit_log(
                "billing.payment_failed",
                user=subscription.user,
                metadata={"invoice_id": invoice.get("id")},
            )
            logger.warning(f"Payment failed for user {subscription.user.email}: invoice={invoice.get('id')}")

        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for failed invoice: {sub_id}")

    # ──────────────────────────────────
    #  Utilities
    # ──────────────────────────────────

    @staticmethod
    def get_plan_limits(plan: str) -> dict:
        """Get the feature limits for a plan."""
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])

    @staticmethod
    def check_limit(*, user, metric: str) -> bool:
        """Check if user is within their plan limit for a given metric. Returns True if OK."""
        plan = getattr(user, "plan", "starter")
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])
        limit = limits.get(metric, 0)

        if limit == -1:
            return True  # Unlimited

        from apps.billing.services.usage_service import UsageService
        usage = UsageService.get_current_usage(user=user)
        current = usage.get(metric, 0)
        return current < limit

    @staticmethod
    def sync_subscription(*, user) -> dict:
        """Sync a user's subscription data from Stripe. Returns the current status."""
        _init_stripe()
        try:
            subscription = user.subscription
            if not subscription.stripe_subscription_id:
                return {"status": subscription.status, "plan": subscription.plan}

            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            StripeService.handle_subscription_updated(stripe_subscription=stripe_sub)
            subscription.refresh_from_db()
            return {"status": subscription.status, "plan": subscription.plan}

        except Subscription.DoesNotExist:
            return {"status": "none", "plan": "starter"}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe sync failed: {e}")
            return {"status": "unknown", "plan": getattr(user, "plan", "starter")}
