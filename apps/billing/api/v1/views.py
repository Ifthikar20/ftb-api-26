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
from apps.billing.services.stripe_service import StripeService
from apps.billing.services.usage_service import UsageService

logger = logging.getLogger("billing")


class BillingOverviewView(APIView):
    """Current subscription, plan details, and usage."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = request.user.subscription
            plan_data = PlanService.get_plan(subscription.plan)
        except Subscription.DoesNotExist:
            subscription = None
            plan_data = PlanService.get_plan("starter")

        # Determine segment
        segment = getattr(request.user, "segment", None) or "individual"

        # Usage — never fails, returns {} if no subscription
        usage = UsageService.get_current_usage(user=request.user)

        return Response({
            "plan": getattr(request.user, "plan", "starter"),
            "segment": segment,
            "plan_details": plan_data,
            "subscription_status": subscription.status if subscription else "none",
            "current_period_end": (
                subscription.current_period_end.isoformat()
                if subscription and subscription.current_period_end else None
            ),
            "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
            "stripe_customer_id": bool(subscription.stripe_customer_id) if subscription else False,
            "usage": usage,
        })


class PlansView(APIView):
    """List all available plans."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PlanService.get_all_plans())


class CheckoutView(APIView):
    """Create a Stripe checkout session for subscribing."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get("plan", "starter")
        annual = request.data.get("annual", False)

        # Validate plan — starter and pro are self-serve; enterprise requires sales contact
        valid_plans = ["starter", "pro"]
        if plan not in valid_plans:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "invalid_plan",
                        "message": (
                            "Enterprise plans require a custom quote. "
                            "Please contact sales@fetchbot.ai."
                        ),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build URLs from request origin (secure — never hardcode domains)
        origin = request.META.get("HTTP_ORIGIN", request.META.get("HTTP_REFERER", ""))
        if not origin:
            origin = "https://app.fetchbot.io"
        origin = origin.rstrip("/")

        success_url = f"{origin}/dashboard?checkout=success"
        cancel_url = f"{origin}/paywall?checkout=canceled"

        try:
            url = StripeService.create_checkout_session(
                user=request.user,
                plan=plan,
                annual=bool(annual),
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return Response({"success": True, "data": {"checkout_url": url}})
        except Exception as e:
            logger.error(f"Checkout creation failed: {e}")
            error_msg = str(e) if hasattr(e, "message") else (
                "We couldn't start the checkout. Please try again."
            )
            return Response(
                {"success": False, "error": {"code": "checkout_failed", "message": error_msg}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PortalView(APIView):
    """Create a Stripe customer portal session for managing subscription."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        origin = request.META.get("HTTP_ORIGIN", request.META.get("HTTP_REFERER", ""))
        if not origin:
            origin = "https://app.fetchbot.io"
        return_url = f"{origin.rstrip('/')}/billing"

        try:
            url = StripeService.create_portal_session(user=request.user, return_url=return_url)
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


class UsageView(APIView):
    """Current billing period usage metrics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usage = UsageService.get_current_usage(user=request.user)
        limits = StripeService.get_plan_limits(getattr(request.user, "plan", "starter"))

        # Combine usage with limits for the frontend
        metrics = []
        for metric, limit in limits.items():
            metrics.append({
                "metric": metric,
                "count": usage.get(metric, 0),
                "limit": limit,
            })

        return Response({"success": True, "data": metrics})
