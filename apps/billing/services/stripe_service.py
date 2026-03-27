"""
Stripe integration service — hardened for production.

Security & resilience features:
    - Circuit breaker wrapping on all Stripe API calls
    - Exponential backoff retry for transient errors
    - select_for_update() on subscription writes (race condition prevention)
    - Graceful degradation when Stripe is unavailable
    - Full audit logging via core.logging.audit_logger
"""

import logging
import time
from datetime import datetime
from functools import wraps

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.billing.models import Invoice, Subscription
from apps.billing.services.circuit_breaker import stripe_circuit, with_circuit_breaker
from core.exceptions import GrowthPilotException
from core.logging.audit_logger import audit_log

logger = logging.getLogger("billing")

# ── Stripe Price IDs — 2-tier model ──
PLAN_PRICE_IDS = {
    "individual": getattr(settings, "STRIPE_INDIVIDUAL_PRICE_ID", ""),
    # Enterprise is custom — no self-serve checkout
}

PLAN_PRICE_IDS_ANNUAL = {
    "individual": getattr(settings, "STRIPE_INDIVIDUAL_ANNUAL_PRICE_ID", ""),
}

# Legacy mappings for backward compatibility
_LEGACY_PLAN_MAP = {
    "starter": "individual",
    "growth": "individual",
    "free": "individual",
    "scale": "enterprise",
    "team": "enterprise",
    "business": "enterprise",
}

# Plan limits for enforcement (mirrors constants.py for service-layer use)
PLAN_LIMITS = {
    "individual": {
        "projects": 3,
        "pageviews": 50_000,
        "competitors": 5,
        "team_members": 1,
        "ai_credits": 100,
        "integrations": 2,
    },
    "enterprise": {
        "projects": -1,
        "pageviews": -1,
        "competitors": -1,
        "team_members": -1,
        "ai_credits": -1,
        "integrations": -1,
    },
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


def _resolve_plan(plan: str) -> str:
    """Map legacy plan names to the 2-tier model."""
    return _LEGACY_PLAN_MAP.get(plan, plan)


def _retry_on_transient(max_retries=3, base_delay=1.0):
    """
    Decorator: retry Stripe calls on transient errors with exponential backoff.
    Only retries APIConnectionError and RateLimitError.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (stripe.error.APIConnectionError, stripe.error.RateLimitError) as e:
                    last_error = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Stripe transient error in {func.__name__} "
                        f"(attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            raise last_error
        return wrapper
    return decorator


class StripeService:
    # ──────────────────────────────────
    #  Customer Management
    # ──────────────────────────────────

    @staticmethod
    @_retry_on_transient(max_retries=3)
    @with_circuit_breaker()
    def get_or_create_customer(*, user) -> str:
        """Get or create a Stripe customer for this user."""
        _init_stripe()
        subscription, _ = Subscription.objects.get_or_create(user=user)

        if subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=getattr(user, "full_name", user.email),
            metadata={"user_id": str(user.id), "segment": getattr(user, "segment", "individual")},
        )

        subscription.stripe_customer_id = customer.id
        subscription.save(update_fields=["stripe_customer_id"])
        audit_log("billing.customer_created", user=user, metadata={"customer_id": customer.id})
        return customer.id

    # ──────────────────────────────────
    #  Checkout Session
    # ──────────────────────────────────

    @staticmethod
    @_retry_on_transient(max_retries=2)
    @with_circuit_breaker()
    def create_checkout_session(*, user, plan: str, annual: bool = False,
                                 success_url: str, cancel_url: str) -> str:
        """Create a Stripe checkout session URL for subscribing."""
        _init_stripe()
        plan = _resolve_plan(plan)
        customer_id = StripeService.get_or_create_customer(user=user)

        price_map = PLAN_PRICE_IDS_ANNUAL if annual else PLAN_PRICE_IDS
        price_id = price_map.get(plan, "")

        if not price_id:
            raise GrowthPilotException(
                "This plan is not available for checkout yet.",
                code="plan_not_available",
                status_code=400,
            )

        # Prevent double checkout if already subscribed
        try:
            existing = user.subscription
            if existing.status == "active" and existing.stripe_subscription_id:
                raise GrowthPilotException(
                    "You already have an active subscription. "
                    "Use 'Manage Subscription' to change your plan.",
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
    @_retry_on_transient(max_retries=2)
    @with_circuit_breaker()
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
    #  Webhook Handlers (called inside atomic transaction)
    # ──────────────────────────────────

    @staticmethod
    def handle_checkout_completed(*, session: dict) -> None:
        """Handle checkout.session.completed — activate subscription."""
        user_id = session.get("metadata", {}).get("user_id")
        plan = _resolve_plan(session.get("metadata", {}).get("plan", "individual"))

        if not user_id:
            logger.warning("Checkout completed but no user_id in metadata.")
            return

        try:
            from apps.accounts.models import User
            user = User.objects.get(id=user_id)

            # Lock the subscription row to prevent concurrent writes
            subscription, created = Subscription.objects.select_for_update().get_or_create(
                user=user
            )
            subscription.plan = plan
            subscription.status = "active"
            subscription.stripe_subscription_id = session.get("subscription")
            subscription.stripe_customer_id = session.get(
                "customer", subscription.stripe_customer_id
            )
            subscription.save()

            user.plan = plan
            user.save(update_fields=["plan"])

            audit_log("billing.subscription_activated", user=user, metadata={"plan": plan})
            logger.info(f"Subscription activated: user={user.email}, plan={plan}")

        except Exception as e:
            logger.error(f"Checkout completion handler failed: {e}", exc_info=True)
            raise  # Re-raise so the webhook handler records the error

    @staticmethod
    def handle_subscription_updated(*, stripe_subscription: dict) -> None:
        """Handle subscription.updated and subscription.deleted webhooks."""
        sub_id = stripe_subscription.get("id")
        try:
            # Lock the row to prevent race conditions
            subscription = Subscription.objects.select_for_update().get(
                stripe_subscription_id=sub_id
            )
            old_status = subscription.status
            new_status = stripe_subscription.get("status", old_status)

            subscription.status = new_status
            subscription.cancel_at_period_end = stripe_subscription.get(
                "cancel_at_period_end", False
            )

            # Update period dates
            period = stripe_subscription.get("current_period_start")
            if period and isinstance(period, int | float):
                subscription.current_period_start = timezone.make_aware(
                    datetime.fromtimestamp(period)
                )

            period_end = stripe_subscription.get("current_period_end")
            if period_end and isinstance(period_end, int | float):
                subscription.current_period_end = timezone.make_aware(
                    datetime.fromtimestamp(period_end)
                )

            # Update plan if items contain a known price
            items = stripe_subscription.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                all_prices = {**PLAN_PRICE_IDS, **PLAN_PRICE_IDS_ANNUAL}
                for plan_name, pid in all_prices.items():
                    if pid and pid == price_id:
                        resolved = _resolve_plan(plan_name)
                        subscription.plan = resolved
                        subscription.user.plan = resolved
                        subscription.user.save(update_fields=["plan"])
                        break

            subscription.save()

            # If canceled, downgrade to individual
            if new_status == "canceled" and old_status != "canceled":
                subscription.user.plan = "individual"
                subscription.user.save(update_fields=["plan"])
                audit_log("billing.subscription_canceled", user=subscription.user)
                logger.info(f"Subscription canceled: user={subscription.user.email}")

            logger.info(f"Subscription updated: {sub_id}, status={new_status}")

        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found for update: {sub_id}")

    @staticmethod
    def handle_invoice_paid(*, invoice: dict) -> None:
        """Handle invoice.paid — store invoice record."""
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
            logger.info(
                f"Invoice recorded: {invoice['id']}, "
                f"amount=${invoice.get('amount_paid', 0) / 100:.2f}"
            )

        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for invoice: {sub_id}")

    @staticmethod
    def handle_invoice_payment_failed(*, invoice: dict) -> None:
        """Handle invoice.payment_failed — mark subscription as past_due."""
        sub_id = invoice.get("subscription")
        if not sub_id:
            return

        try:
            subscription = Subscription.objects.select_for_update().get(
                stripe_subscription_id=sub_id
            )
            subscription.status = "past_due"
            subscription.save(update_fields=["status"])

            audit_log(
                "billing.payment_failed",
                user=subscription.user,
                metadata={"invoice_id": invoice.get("id")},
            )
            logger.warning(
                f"Payment failed for user {subscription.user.email}: "
                f"invoice={invoice.get('id')}"
            )

        except Subscription.DoesNotExist:
            logger.warning(f"No subscription for failed invoice: {sub_id}")

    # ──────────────────────────────────
    #  Utilities
    # ──────────────────────────────────

    @staticmethod
    def get_plan_limits(plan: str) -> dict:
        """Get the feature limits for a plan."""
        plan = _resolve_plan(plan)
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["individual"])

    @staticmethod
    def check_limit(*, user, metric: str) -> bool:
        """Check if user is within their plan limit. Returns True if OK."""
        plan = _resolve_plan(getattr(user, "plan", "individual"))
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["individual"])
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

            if not stripe_circuit.is_available:
                # Circuit breaker open — return cached data
                logger.info(
                    f"Circuit open — returning cached subscription for {user.email}"
                )
                return {"status": subscription.status, "plan": subscription.plan}

            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            stripe_circuit.record_success()

            with transaction.atomic():
                StripeService.handle_subscription_updated(stripe_subscription=stripe_sub)

            subscription.refresh_from_db()
            return {"status": subscription.status, "plan": subscription.plan}

        except Subscription.DoesNotExist:
            return {"status": "none", "plan": "individual"}
        except (stripe.error.APIConnectionError, stripe.error.RateLimitError) as e:
            stripe_circuit.record_failure()
            logger.error(f"Stripe sync failed (transient): {e}")
            # Return cached data — don't break the UI
            try:
                return {"status": user.subscription.status, "plan": user.subscription.plan}
            except Subscription.DoesNotExist:
                return {"status": "unknown", "plan": "individual"}
        except stripe.error.StripeError as e:
            logger.error(f"Stripe sync failed: {e}")
            return {"status": "unknown", "plan": getattr(user, "plan", "individual")}
