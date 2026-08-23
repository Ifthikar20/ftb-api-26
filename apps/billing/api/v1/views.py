"""
Billing API views — hardened for production.

All views handle Stripe unavailability gracefully by returning cached data.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import Invoice, Subscription
from apps.billing.services.plan_service import PlanService

logger = logging.getLogger("billing")


def _safe_origin(request) -> str:
    """Origin used to build checkout/portal return URLs.

    The Origin/Referer headers are attacker-controllable, and Polar's
    success redirect is NOT signed — trusting them blindly would let a
    crafted request bounce a paying customer to a foreign site after
    checkout. Only origins on the CORS allowlist (plus FRONTEND_URL)
    are honored; anything else falls back to FRONTEND_URL.
    """
    from urllib.parse import urlsplit

    from django.conf import settings as dj_settings

    allowed = set(getattr(dj_settings, "CORS_ALLOWED_ORIGINS", []) or [])
    canonical = getattr(dj_settings, "FRONTEND_URL", "").rstrip("/")
    if canonical:
        allowed.add(canonical)

    raw = request.META.get("HTTP_ORIGIN") or request.META.get("HTTP_REFERER") or ""
    parts = urlsplit(raw)
    candidate = f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""
    if candidate and candidate in allowed:
        return candidate
    return canonical or "https://app.fetchbot.io"


def _client_ip(request) -> str:
    """Customer IP for Polar's location-based tax/currency detection.

    Proxy-aware: the LEFT-most X-Forwarded-For hop is client-controlled
    (a customer could claim a low-tax jurisdiction's IP), so delegate to
    the hardened resolver that only trusts our own proxy hops.
    """
    from core.utils.ua_parser import get_client_ip

    return get_client_ip(request)


class BillingOverviewView(APIView):
    """Current subscription, plan details, and usage."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.billing.services import polar_billing
        from apps.billing.services.plan_limits import (
            plan_for_subscription,
            subscription_state,
        )
        from core.utils.constants import SubscriptionStatus

        try:
            subscription = request.user.subscription
        except Subscription.DoesNotExist:
            subscription = None

        # Stale-state safety net: a paid checkout whose confirm redirect
        # never landed leaves the local row missing while Polar has the
        # subscription — and this page would tell a paying customer they
        # are on the Free plan. When there is neither an access-granting
        # row nor any Polar-managed row, ask Polar before answering.
        # (Rows that already carry a polar_subscription_id are owned by
        # the webhook/confirm sync — do not second-guess them here.)
        if polar_billing.is_configured() and not (
            subscription
            and (
                subscription.polar_subscription_id
                or subscription.status in (
                    SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING,
                )
            )
        ):
            try:
                # Cooldown-limited: at most one Polar round-trip per
                # user per window, so a polling client cannot trip the
                # shared circuit breaker.
                subscription = polar_billing.self_heal_from_polar(request.user)
            except Exception:
                logger.warning(
                    "Billing overview Polar state sync failed for %s",
                    request.user.id, exc_info=True,
                )

        # The mirror image of the guard above: a Polar-managed TRIALING
        # row whose trial end has passed is re-verified (cooldown-
        # limited, never raises) so a converted trial reads Active and a
        # failed charge reads Past due instead of "trialing" forever.
        subscription = polar_billing.reverify_ended_trial(request.user, subscription)
        state = subscription_state(subscription)

        # The plan the account is ACTUALLY on: an active/trialing
        # subscription grants its tier; everything else is Free. Derived
        # from the row we hold (NOT current_plan_for: the user instance
        # may cache a pre-sync "no subscription" miss), and never from
        # the denormalized user.plan, which defaults to a paid tier and
        # used to leak paid allowances to unsubscribed accounts.
        active_plan = str(plan_for_subscription(subscription))
        plan_data = PlanService.get_plan(active_plan)

        # Determine segment
        segment = getattr(request.user, "segment", None) or "individual"

        return Response({
            "plan": active_plan,
            "segment": segment,
            "plan_details": plan_data,
            # False until the Polar token + product ids are configured —
            # the frontend disables checkout and says so instead of
            # letting the button fail silently.
            "billing_ready": polar_billing.is_configured(),
            "subscription_status": subscription.status if subscription else "none",
            # Shared trial/tier vocabulary (same builder as the session
            # payload) so labels cannot drift between surfaces.
            "tier": state["tier"],
            "is_trialing": state["is_trialing"],
            "trial_end": state["trial_end"],
            # Raw plan on the subscription row (legacy values included).
            # The frontend needs it for non-access-granting states the
            # top-level `plan` reports as free — e.g. a past_due paying
            # customer must still be shown their paid plan, not "Free".
            "subscription_plan": subscription.plan if subscription else None,
            "current_period_end": (
                subscription.current_period_end.isoformat()
                if subscription and subscription.current_period_end else None
            ),
            "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
            # True when this subscription is managed by the billing
            # provider (Polar) — gates the "Manage billing" portal button.
            "managed": bool(subscription.polar_subscription_id) if subscription else False,
            "provider": "polar" if subscription and subscription.polar_subscription_id else None,
        })


class PlansView(APIView):
    """List all available plans."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PlanService.get_all_plans())


class CheckoutView(APIView):
    """Create a Polar checkout session for the Pro plan.

    The old Stripe checkout and the BILLING_DEV_MODE mock path are gone:
    subscribing always goes through Polar's hosted checkout (sandbox
    accepts Stripe test cards, so dev/demo flows use real checkout too).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get("plan", "pro")
        annual = bool(request.data.get("annual", False))

        # Pro is the only self-serve tier; Business requires sales contact.
        legacy_pro_names = {"pro", "individual", "starter", "growth"}
        if plan not in legacy_pro_names:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "invalid_plan",
                        "message": (
                            "Business plans require a custom quote. "
                            "Please contact sales@fetchbot.ai."
                        ),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        origin = _safe_origin(request)

        from apps.billing.services import polar_billing
        from core.exceptions import GrowthPilotException

        try:
            url = polar_billing.create_checkout(
                request.user, annual=annual, origin=origin,
                customer_ip=_client_ip(request),
            )
            return Response({"success": True, "data": {"checkout_url": url}})
        except GrowthPilotException as e:
            # Keep the domain error code (e.g. already_subscribed) — the
            # frontend branches on it to recover instead of just
            # showing a failure toast.
            logger.warning(f"Checkout refused: {e}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": getattr(e, "code", "checkout_failed"),
                        "message": str(e),
                    },
                },
                status=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        except Exception as e:
            # Unexpected failure: log the detail, return only a generic
            # message. Never echo raw exception text to the client — it
            # can carry upstream/internal detail.
            logger.error(f"Checkout creation failed: {e}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "checkout_failed",
                        "message": "We couldn't start the checkout. Please try again.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class CheckoutConfirmView(APIView):
    """Confirm a completed Polar checkout after the success redirect.

    The frontend lands on /dashboard?checkout=success&checkout_id=... and
    posts the id here; we verify it against Polar and sync the
    subscription. This makes activation work in local dev where Polar
    cannot deliver webhooks; in production the webhook does the same
    thing first and this call becomes a no-op re-sync.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        checkout_id = str(request.data.get("checkout_id", "")).strip()
        if not checkout_id:
            return Response(
                {"success": False, "error": {"code": "missing_checkout_id",
                 "message": "checkout_id is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.billing.services import polar_billing

        try:
            result = polar_billing.confirm_checkout(request.user, checkout_id)
            return Response({"success": True, "data": result})
        except Exception as e:
            logger.error("Checkout confirmation failed: %s", e)
            return Response(
                {"success": False, "error": {"code": "confirm_failed",
                 "message": "We couldn't verify the checkout. Refresh in a moment."}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PortalView(APIView):
    """Create a pre-authenticated Polar customer portal session."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return_url = f"{_safe_origin(request)}/billing"

        from apps.billing.services import polar_billing

        try:
            url = polar_billing.portal_url(request.user, return_url=return_url)
            return Response({"success": True, "data": {"portal_url": url}})
        except Exception as e:
            logger.error(f"Portal creation failed: {e}")
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "portal_failed",
                        "message": "We couldn't open the billing portal. Please try again.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubscriptionCancelView(APIView):
    """
    Cancel the current user's subscription at the end of the period.

    Polar-managed subscriptions are updated via the Polar API and then
    re-synced; legacy local-only rows just flip the flag.

    POST /api/v1/billing/cancel/   -> sets cancel_at_period_end = True
    POST /api/v1/billing/resume/   -> sets cancel_at_period_end = False
    """
    permission_classes = [IsAuthenticated]
    cancel = True   # subclass flips to False for resume

    def post(self, request):
        try:
            sub = request.user.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "no_subscription",
                 "message": "You don't have an active subscription."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sub.polar_subscription_id:
            from apps.billing.services import polar_billing

            try:
                sub = polar_billing.set_cancel_at_period_end(
                    request.user, cancel=self.cancel,
                )
            except Exception as e:
                logger.error("Polar cancel/resume failed: %s", e)
                return Response(
                    {"success": False, "error": {"code": "billing_failed",
                     "message": "We couldn't update the subscription. Please try again."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            sub.cancel_at_period_end = self.cancel
            sub.save(update_fields=["cancel_at_period_end", "updated_at"])

        return Response({
            "success": True,
            "data": {
                "cancel_at_period_end": sub.cancel_at_period_end,
                "current_period_end": (
                    sub.current_period_end.isoformat()
                    if sub.current_period_end else None
                ),
            },
        })


class SubscriptionResumeView(SubscriptionCancelView):
    cancel = False


class InvoiceListView(APIView):
    """List all invoices for the current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = request.user.subscription
            invoices = Invoice.objects.filter(subscription=subscription).order_by("-created_at")[:20]
            data = [
                {
                    "id": str(inv.id),
                    "amount_paid": inv.amount_paid,
                    "currency": inv.currency,
                    "status": inv.status,
                    "invoice_pdf": inv.invoice_pdf,
                    "period_start": inv.period_start.isoformat() if inv.period_start else None,
                    "period_end": inv.period_end.isoformat() if inv.period_end else None,
                    "created_at": inv.created_at.isoformat(),
                }
                for inv in invoices
            ]
        except Subscription.DoesNotExist:
            data = []
        return Response({"success": True, "data": data})




class AITokenUsageView(APIView):
    """Aggregate AI token spend for the current user's billing period.

    Same service (apps.metering.services.usage_reader) as the Settings
    page's AIUsageView, so the two surfaces agree by construction —
    previously each ran its own aggregation over a different window.
    Keeps this endpoint's historical envelope keys (cost_usd, call_count)
    for the Billing page card.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.metering.services.usage_reader import get_period_usage

        usage = get_period_usage(request.user)

        def _shape(rows, key):
            return [
                {
                    key: r.get(key) or "",
                    "tokens": int(r.get("tokens") or 0),
                    "cost_usd": float(r.get("cost") or 0),
                }
                for r in rows
            ]

        payload = {
            "period": usage["period"],
            "source": usage["source"],
            "call_count": usage["totals"]["calls"],
            "totals": {
                "input_tokens": usage["totals"]["input_tokens"],
                "output_tokens": usage["totals"]["output_tokens"],
                "total_tokens": usage["totals"]["total_tokens"],
                "cost_usd": usage["totals"]["estimated_cost_usd"],
            },
            "by_provider": _shape(usage["by_provider"], "provider"),
            "by_module": _shape(usage["by_module"], "module"),
            "allowance": usage["allowance"],
        }
        # Bare payload: the global EnvelopeRenderer wraps it once as
        # {success, data}. The old explicit {"success", "data"} return was
        # double-wrapped by that renderer, which is why the Billing card
        # read one envelope level too shallow.
        return Response(payload)


class PaywallDismissView(APIView):
    """POST — record that the user chose to continue on the Free plan.

    Idempotent: repeat calls keep the original dismissal timestamp.
    Paying users are a no-op (the paywall never routes for them) and the
    flag stays unset, so a later lapse re-surfaces the paywall once.
    Deliberately settings-independent: inert but harmless while
    PAYWALL_ENABLED is off.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.utils import timezone

        from apps.billing.services.plan_limits import is_paying
        from core.logging.audit_logger import audit_log

        user = request.user

        if is_paying(user):
            return Response({
                "paywall_dismissed": user.paywall_dismissed_at is not None,
                "dismissed_at": (
                    user.paywall_dismissed_at.isoformat()
                    if user.paywall_dismissed_at else None
                ),
                "already_paying": True,
            })

        if user.paywall_dismissed_at is None:
            user.paywall_dismissed_at = timezone.now()
            user.save(update_fields=["paywall_dismissed_at", "updated_at"])
            audit_log("billing.paywall_dismissed", user=user, request=request)

        return Response({
            "paywall_dismissed": True,
            "dismissed_at": user.paywall_dismissed_at.isoformat(),
            "already_paying": False,
        })
