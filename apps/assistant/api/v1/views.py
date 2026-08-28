"""Ask Cansee assistant API.

Endpoints:
    GET  /api/v1/assistant/status/            - is the feature available?
    POST /api/v1/assistant/<website_id>/ask/  - answer a question

Tenant isolation is enforced by TenantScopedAPIView.get_website (404/403
unless the caller owns the website) plus user = request.user; no
identifier is ever read from the request body.

Availability: settings.ASSISTANT_ENABLED is a deployment-wide
entitlement/maintenance switch. When it is off, /ask/ returns 503 with
the configured maintenance message and the UI degrades to a maintenance
card instead of the composer.
"""
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant.api.v1.serializers import AssistantAskSerializer
from apps.assistant.services.orchestrator import answer
from core.resilience import TokenBucket
from core.views.base import TenantScopedAPIView

# Cap history folded into the prompt regardless of what the client sends.
_MAX_HISTORY = 12


def _maintenance_message() -> str:
    return getattr(
        settings, "ASSISTANT_MAINTENANCE_MESSAGE",
        "Ask Cansee is temporarily unavailable.",
    )


def _is_enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_ENABLED", True))


def _ask_bucket(user_id) -> TokenBucket:
    """Per-user throttle. Each ask is one LLM call + one embedding, so
    keep it modest: burst 15, ~18/min steady state."""
    return TokenBucket(
        name=f"assistant-ask:{user_id}",
        capacity=15,
        refill_per_second=0.3,
    )


class AssistantStatusView(APIView):
    """Feature availability, so the UI can hide the trigger or show a
    maintenance card without first firing a failing question."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled = _is_enabled()
        return Response({
            "enabled": enabled,
            "message": "" if enabled else _maintenance_message(),
        })


class AssistantAskView(TenantScopedAPIView):
    def post(self, request, website_id):
        # Entitlement gate first: when the feature is off nobody reaches
        # the model, regardless of tenant or plan.
        if not _is_enabled():
            return Response(
                {"error": {"code": "assistant_disabled",
                           "message": _maintenance_message()}},
                status=503,
            )

        website = self.get_website(website_id)  # tenant gate (404/403)

        if not _ask_bucket(request.user.id).try_acquire():
            return Response(
                {"error": "You're asking a lot very fast. Give it a few "
                          "seconds and try again."},
                status=429,
            )

        serializer = AssistantAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = answer(
            user=request.user,
            website=website,
            question=data["question"],
            history=(data.get("history") or [])[-_MAX_HISTORY:],
        )
        return Response(result)
