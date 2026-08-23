"""
Billing health check endpoint.

Returns the current state of the billing service:
    - Polar configuration (products + token present)
    - Polar circuit breaker state
    - Webhook event backlog

Staff-only: breaker state and webhook backlog are operational detail an
attacker could use to time abuse (e.g. probe while the breaker is
stressed). Liveness monitoring uses the app-level /health/ endpoint.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import BillingEvent
from apps.metering import polar_client


class BillingHealthView(APIView):
    """
    GET /api/v1/billing/health/

    Returns billing service health status for staff/ops accounts.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.billing.services import polar_billing

        circuit_status = polar_client.breaker().status()

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
        if not polar_billing.is_configured():
            overall = "unconfigured"
        elif circuit_status["state"] == "open":
            overall = "degraded"
        elif recent_failures > 5:
            overall = "degraded"
        elif circuit_status["state"] == "half_open":
            overall = "recovering"
        else:
            overall = "healthy"

        return Response({
            "status": overall,
            "polar": {
                "configured": polar_billing.is_configured(),
                "circuit_breaker": circuit_status,
            },
            "webhooks": {
                "last_event_at": last_webhook_at,
                "unprocessed_count": unprocessed_count,
                "recent_failures_1h": recent_failures,
            },
            "timestamp": timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
