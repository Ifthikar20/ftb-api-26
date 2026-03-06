from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.billing.models import Subscription, Invoice
from apps.billing.services.stripe_service import StripeService
from apps.billing.services.plan_service import PlanService
from apps.billing.services.usage_service import UsageService


class BillingOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = request.user.subscription
            plan_data = PlanService.get_plan(subscription.plan)
        except Subscription.DoesNotExist:
            subscription = None
            plan_data = PlanService.get_plan("starter")

        usage = UsageService.get_current_usage(user=request.user)

        return Response({
            "plan": request.user.plan,
            "plan_details": plan_data,
            "subscription_status": subscription.status if subscription else "none",
            "current_period_end": subscription.current_period_end if subscription else None,
            "usage": usage,
        })


class PlansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PlanService.get_all_plans())


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get("plan", "growth")
        success_url = request.data.get("success_url", "https://app.growthpilot.io/billing/success")
        cancel_url = request.data.get("cancel_url", "https://app.growthpilot.io/billing")

        url = StripeService.create_checkout_session(
            user=request.user,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return Response({"checkout_url": url})


class PortalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return_url = request.data.get("return_url", "https://app.growthpilot.io/billing")
        url = StripeService.create_portal_session(user=request.user, return_url=return_url)
        return Response({"portal_url": url})


class InvoiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = request.user.subscription
            invoices = Invoice.objects.filter(subscription=subscription)
            data = [
                {
                    "id": str(inv.id),
                    "amount_paid": inv.amount_paid,
                    "currency": inv.currency,
                    "status": inv.status,
                    "invoice_pdf": inv.invoice_pdf,
                    "created_at": inv.created_at.isoformat(),
                }
                for inv in invoices
            ]
        except Subscription.DoesNotExist:
            data = []
        return Response(data)


class UsageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usage = UsageService.get_current_usage(user=request.user)
        return Response(usage)
