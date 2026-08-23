"""
Polar-backed billing: product catalog, checkout, plan sync, portal.

Replaces the Stripe checkout path. The flow:

  1. `polar_billing_bootstrap` creates the Pro products in Polar
     (monthly $45 / annual $450, 7-day trial) and their ids go into env.
  2. CheckoutView -> create_checkout() -> redirect the user to Polar's
     hosted checkout (sandbox accepts Stripe test cards).
  3. The user returns to /dashboard?checkout=success&checkout_id=... and
     the frontend calls CheckoutConfirmView -> confirm_checkout(), which
     pulls the checkout + customer state from Polar and updates the local
     Subscription row and user.plan. (In production the webhook does the
     same server-side; the redirect confirmation makes local dev work
     without a public webhook URL.)
  4. sync_from_customer_state() is the single writer for subscription
     state: webhook, confirm, and manual refresh all converge here.

Populating Subscription.current_period_start/end here is what flips
every usage window (metering Pass 1's billing_period_for seam) from
calendar months to real billing cycles — by design, no other code
changes needed.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.billing.models import Subscription
from apps.metering import polar_client
from core.exceptions import GrowthPilotException
from core.logging.audit_logger import audit_log
from core.utils.constants import Plan, SubscriptionStatus

logger = logging.getLogger("billing")

PRODUCT_PRO_MONTHLY = "FetchBot Pro (Monthly)"
PRODUCT_PRO_ANNUAL = "FetchBot Pro (Annual)"

# Polar subscription status -> local SubscriptionStatus. Anything that
# still grants access maps to ACTIVE/TRIALING; terminal states to
# CANCELED so entitlement gates close.
_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.TRIALING,
    "past_due": SubscriptionStatus.PAST_DUE,
    "incomplete": SubscriptionStatus.INCOMPLETE,
    "incomplete_expired": SubscriptionStatus.CANCELED,
    "canceled": SubscriptionStatus.CANCELED,
    "revoked": SubscriptionStatus.CANCELED,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "paused": SubscriptionStatus.CANCELED,
}


def is_configured() -> bool:
    return bool(
        polar_client.is_configured()
        and settings.POLAR_PRODUCT_PRO_MONTHLY_ID
        and settings.POLAR_PRODUCT_PRO_ANNUAL_ID
    )


def _require_configured() -> None:
    if not is_configured():
        raise GrowthPilotException(
            "Billing is not configured yet. Please try again later.",
            code="billing_not_configured",
            status_code=503,
        )


def _product_id_for(annual: bool) -> str:
    return (
        settings.POLAR_PRODUCT_PRO_ANNUAL_ID
        if annual
        else settings.POLAR_PRODUCT_PRO_MONTHLY_ID
    )


def _plan_for_product(product_id: str) -> str | None:
    if product_id in (
        settings.POLAR_PRODUCT_PRO_MONTHLY_ID,
        settings.POLAR_PRODUCT_PRO_ANNUAL_ID,
    ):
        return Plan.PRO
    return None


# ── Catalog ───────────────────────────────────────────────────────────────


def bootstrap_products() -> dict[str, str]:
    """Find-or-create the Pro products; returns {name: product_id}.

    Idempotent by product name. Prices are USD cents; trial is 7 days on
    both cadences (the product-level default the checkout inherits).
    """
    wanted = {
        PRODUCT_PRO_MONTHLY: {
            "name": PRODUCT_PRO_MONTHLY,
            "description": "FetchBot Pro subscription, billed monthly.",
            "recurring_interval": "month",
            "prices": [{"amount_type": "fixed", "price_amount": 45_00}],
            "trial_interval": "day",
            "trial_interval_count": 7,
        },
        PRODUCT_PRO_ANNUAL: {
            "name": PRODUCT_PRO_ANNUAL,
            "description": "FetchBot Pro subscription, billed yearly (2 months free).",
            "recurring_interval": "year",
            "prices": [{"amount_type": "fixed", "price_amount": 450_00}],
            "trial_interval": "day",
            "trial_interval_count": 7,
        },
    }
    existing = {p.name: str(p.id) for p in polar_client.list_products()}
    out = {}
    for name, request in wanted.items():
        if name in existing:
            out[name] = existing[name]
            continue
        created = polar_client.create_product(request)
        out[name] = str(created.id)
    return out


# ── Checkout ──────────────────────────────────────────────────────────────

# Minimum interval between request-path Polar state syncs per user. The
# overview and pre-checkout self-heals run on hot authenticated paths;
# without a floor, one account polling them could drive unbounded Polar
# API calls and trip the SHARED circuit breaker for every user.
_SELF_HEAL_COOLDOWN_S = 60


def self_heal_from_polar(user) -> Subscription | None:
    """Rate-limited wrapper around sync_from_customer_state for
    request-path self-heals. cache.add is atomic: at most one Polar
    round-trip per user per cooldown window; every other caller in the
    window just reads the local row."""
    key = f"billing:selfheal:{user.id}"
    if not cache.add(key, 1, _SELF_HEAL_COOLDOWN_S):
        return Subscription.objects.filter(user=user).first()
    return sync_from_customer_state(user)


def create_checkout(user, *, annual: bool, origin: str, customer_ip: str = "") -> str:
    """Create a Polar checkout for Pro; returns the hosted checkout URL."""
    _require_configured()

    sub = Subscription.objects.filter(user=user).first()
    if not (
        sub
        and (
            sub.polar_subscription_id
            or sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
        )
    ):
        # The local row says unpaid, but Polar may know better: a paid
        # checkout whose confirm redirect never landed (closed tab,
        # broken success_url) leaves the local DB stale, the paywall
        # gate looping, and Polar refusing the duplicate checkout with
        # "You already have an active subscription" — a trap with no
        # exit. Self-heal from Polar's customer state before creating
        # anything. Rows already carrying a polar_subscription_id are
        # owned by the webhook/confirm sync and are not second-guessed
        # (an ex-subscriber goes straight to a fresh checkout).
        # Best-effort: a sync failure must not block a legitimate first
        # checkout.
        try:
            sub = self_heal_from_polar(user)
        except Exception:
            logger.warning(
                "Pre-checkout Polar state sync failed for %s; continuing",
                user.id, exc_info=True,
            )
    if sub and sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        raise GrowthPilotException(
            "You already have an active subscription. Use Manage billing "
            "to change your plan.",
            code="already_subscribed",
            status_code=400,
        )

    # {CHECKOUT_ID} is substituted by Polar on redirect; the billing page
    # posts it to /billing/confirm/ so activation works without waiting
    # for a webhook (which cannot reach localhost in dev). The redirect
    # itself is NOT signed by Polar, which is why confirmation always
    # re-verifies the checkout against the API before granting anything.
    success_url = f"{origin}/billing?checkout=success&checkout_id={{CHECKOUT_ID}}"
    common = {
        "product_ids": [_product_id_for(annual)],
        "external_customer_id": str(user.id),
        "success_url": success_url,
        "metadata": {"plan": str(Plan.PRO), "annual": annual},
        "customer_ip_address": customer_ip or None,
    }
    try:
        checkout = polar_client.create_checkout(customer_email=user.email, **common)
    except polar_client.PolarRejected as exc:
        # Polar validates that the email's domain can receive mail; dev
        # and test accounts (and the odd real user on a mail-less
        # domain) fail that check. Retry without prefilling — the hosted
        # checkout then asks the customer to type an email, and identity
        # stays bound through external_customer_id.
        if "customer_email" not in str(exc):
            raise
        # Log the user id, not the email — no PII in application logs.
        logger.warning(
            "Checkout email for user %s rejected by Polar; retrying without prefill",
            user.id,
        )
        checkout = polar_client.create_checkout(customer_email=None, **common)
    audit_log(
        "billing.checkout_created",
        user=user,
        metadata={"checkout_id": str(checkout.id), "annual": annual, "provider": "polar"},
    )
    url = str(checkout.url)
    # Match the app's light theme on the hosted page.
    return url + ("&" if "?" in url else "?") + "theme=light"


def confirm_checkout(user, checkout_id: str) -> dict:
    """Post-redirect confirmation: verify the checkout belongs to this
    user and succeeded, then sync subscription state from Polar."""
    _require_configured()
    checkout = polar_client.get_checkout(checkout_id)

    if str(getattr(checkout, "external_customer_id", "") or "") != str(user.id):
        raise GrowthPilotException(
            "This checkout does not belong to your account.",
            code="checkout_mismatch",
            status_code=403,
        )

    status = str(getattr(checkout, "status", ""))
    if status not in ("succeeded", "confirmed"):
        return {"status": status, "active": False}

    sub = sync_from_customer_state(user)
    return {
        "status": status,
        "active": bool(
            sub
            and sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
        ),
        "plan": getattr(sub, "plan", None),
    }


# ── State sync (the single writer) ────────────────────────────────────────


def sync_from_customer_state(user) -> Subscription | None:
    """Pull the customer state from Polar and mirror it locally.

    Called from checkout confirmation, the webhook, and manual refresh.
    Picks the newest access-granting subscription; if none exists and the
    local row is Polar-managed, it is marked canceled (plan value is kept
    for display; entitlement gates read status).
    """
    try:
        state = polar_client.get_customer_state(str(user.id))
    except polar_client.PolarRejected:
        # No Polar customer yet — nothing to sync.
        return Subscription.objects.filter(user=user).first()

    subs = list(getattr(state, "active_subscriptions", None) or [])
    chosen = None
    for s in subs:
        plan = _plan_for_product(str(getattr(s, "product_id", "")))
        if plan is None:
            continue
        if chosen is None or (
            getattr(s, "started_at", None)
            and getattr(chosen[0], "started_at", None)
            and s.started_at > chosen[0].started_at
        ):
            chosen = (s, plan)

    with transaction.atomic():
        sub, created = Subscription.objects.select_for_update().get_or_create(user=user)
        if chosen is not None:
            polar_sub, plan = chosen
            sub.polar_subscription_id = str(polar_sub.id)
            sub.plan = plan
            # SDK statuses are enums whose str() is "Status.TRIALING" —
            # unwrap .value before mapping or trials render as active.
            raw_status = getattr(polar_sub, "status", "active")
            raw_status = getattr(raw_status, "value", raw_status)
            sub.status = _STATUS_MAP.get(str(raw_status), SubscriptionStatus.ACTIVE)
            sub.current_period_start = getattr(polar_sub, "current_period_start", None)
            sub.current_period_end = getattr(polar_sub, "current_period_end", None)
            sub.cancel_at_period_end = bool(
                getattr(polar_sub, "cancel_at_period_end", False)
            )
            sub.save()
            if user.plan != plan:
                user.plan = plan
                user.save(update_fields=["plan"])
        elif sub.polar_subscription_id:
            # Previously Polar-managed, now gone upstream: access ends.
            sub.status = SubscriptionStatus.CANCELED
            sub.save(update_fields=["status", "updated_at"])
        elif created:
            # get_or_create minted this row a moment ago and Polar has
            # nothing for the user. The model default (TRIALING) would
            # leak paid-tier feature gates through current_plan_for, so
            # a row born from an empty sync must deny access.
            sub.status = SubscriptionStatus.CANCELED
            sub.save(update_fields=["status", "updated_at"])

    audit_log(
        "billing.synced_from_polar",
        user=user,
        metadata={"status": sub.status, "plan": sub.plan},
    )
    return sub


# ── Portal / lifecycle ────────────────────────────────────────────────────


def portal_url(user, *, return_url: str | None = None) -> str:
    _require_configured()
    return polar_client.create_portal_url(str(user.id), return_url=return_url)


def set_cancel_at_period_end(user, cancel: bool) -> Subscription:
    """Cancel at period end (or resume) via the Polar API, then re-sync."""
    _require_configured()
    sub = Subscription.objects.filter(user=user).first()
    if not sub or not sub.polar_subscription_id:
        raise GrowthPilotException(
            "No active subscription to update.",
            code="no_subscription",
            status_code=400,
        )
    polar_client.update_subscription(
        sub.polar_subscription_id, {"cancel_at_period_end": cancel}
    )
    audit_log(
        "billing.cancel_at_period_end" if cancel else "billing.resumed",
        user=user,
        metadata={"subscription_id": sub.polar_subscription_id},
    )
    synced = sync_from_customer_state(user)
    return synced or sub


def touch_synced_at(sub: Subscription) -> None:
    sub.updated_at = timezone.now()
