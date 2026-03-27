"""
Billing health check endpoint.

Returns the current state of the billing service:
    - Stripe API connectivity
    - Circuit breaker state
    - Last webhook event timestamp
    - Unprocessed event count

No authentication required — designed for monitoring systems (e.g., Datadog, PagerDuty).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import BillingEvent
from apps.billing.services.circuit_breaker import stripe_circuit


class BillingHealthView(APIView):
    """
    GET /api/v1/billing/health/

    Returns billing service health status for monitoring.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No auth required for health checks

    def get(self, request):
        circuit_status = stripe_circuit.get_status()

        # Last webhook event
        last_event = BillingEvent.objects.order_by("-created_at").first()
        last_webhook_at = last_event.created_at.isoformat() if last_event else None

        # Unprocessed events (failed or pending)
        unprocessed_count = BillingEvent.objects.filter(processed=False).count()

        # Failed events in last hour
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        recent_failures = BillingEvent.objects.filter(
            processed=False,
            created_at__gte=one_hour_ago,
        ).count()

        # Overall status
        if circuit_status["state"] == "open":
            overall = "degraded"
        elif recent_failures > 5:
            overall = "degraded"
        elif circuit_status["state"] == "half_open":
            overall = "recovering"
        else:
            overall = "healthy"

        return Response({
            "status": overall,
            "stripe": {
                "circuit_breaker": circuit_status,
            },
            "webhooks": {
                "last_event_at": last_webhook_at,
                "unprocessed_count": unprocessed_count,
                "recent_failures_1h": recent_failures,
            },
            "timestamp": timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
