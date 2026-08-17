"""REST endpoints for hireable agents."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.api.v1.serializers import (
    AgentActionSerializer,
    AgentInsightSerializer,
    AgentMessageSerializer,
    HiredAgentSerializer,
)
from apps.agents.catalog import available_for, get_spec
from apps.agents.models import AgentAction, AgentInsight, AgentMessage, HiredAgent
from apps.billing.services import plan_limits
from core.exceptions import ResourceNotFound
from core.interceptors.pagination import StandardPagination


def _get_hired(user, hired_id) -> HiredAgent:
    try:
        return HiredAgent.objects.select_related("website", "user", "slack_connection").get(
            id=hired_id, user=user
        )
    except HiredAgent.DoesNotExist:
        raise ResourceNotFound("Agent not found.") from None


class AgentCatalogView(APIView):
    """GET — the agent catalog the user's plan can hire, plus capacity info."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        specs = available_for(request.user)
        max_agents = plan_limits.get_numeric_limit(request.user, "max_agents")
        hired_count = HiredAgent.objects.filter(user=request.user, is_active=True).count()
        return Response({
            "data": [
                {
                    "key": s.key, "name": s.name, "tagline": s.tagline,
                    "domain": s.domain, "icon": s.icon,
                    "allowed_action_types": s.allowed_action_types,
                }
                for s in specs
            ],
            "capacity": {
                "max_agents": max_agents,
                "hired_count": hired_count,
                "can_hire": max_agents == -1 or hired_count < max_agents,
            },
        })


class HireAgentView(APIView):
    """POST — hire an agent for a website (gated by plan max_agents)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        agent_key = request.data.get("agent_key", "")
        if get_spec(agent_key) is None:
            return Response({"error": f"Unknown agent: {agent_key}"},
                            status=status.HTTP_400_BAD_REQUEST)

        from apps.websites.services.website_service import WebsiteService
        website = WebsiteService.get_for_user(
            user=request.user, website_id=request.data.get("website_id"),
        )

        active_count = HiredAgent.objects.filter(user=request.user, is_active=True).count()
        if not plan_limits.is_within_limit(request.user, "max_agents", active_count):
            return Response(
                {"error": "agent_limit_reached",
                 "detail": "Your plan's agent limit is reached. Upgrade to hire more."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        slack_connection_id = request.data.get("slack_connection_id")
        slack_connection = None
        if slack_connection_id:
            from apps.notifications.models import IntegrationConnection
            slack_connection = IntegrationConnection.objects.filter(
                id=slack_connection_id, user=request.user
            ).first()

        agent, created = HiredAgent.objects.get_or_create(
            website=website, agent_key=agent_key,
            defaults={
                "user": request.user,
                "created_by": request.user,
                "frequency": request.data.get("frequency", HiredAgent.FREQUENCY_DAILY),
                "slack_connection": slack_connection,
            },
        )
        if not created and not agent.is_active:
            agent.is_active = True
            agent.save(update_fields=["is_active", "updated_at"])

        return Response(
            HiredAgentSerializer(agent).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class HiredAgentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = HiredAgent.objects.filter(user=request.user).select_related("website")
        website_id = request.query_params.get("website")
        if website_id:
            qs = qs.filter(website_id=website_id)
        return Response({"data": HiredAgentSerializer(qs, many=True).data})


class HiredAgentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        return Response(HiredAgentSerializer(agent).data)

    def patch(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        # Pass request context so the serializer can enforce per-tenant
        # ownership on writable relations (slack_connection). website and
        # agent_key are read-only on the serializer and cannot be changed here.
        serializer = HiredAgentSerializer(
            agent, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        agent.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HiredAgentRunNowView(APIView):
    """POST — trigger an immediate run (handy for demos / first insight)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        from apps.agents.tasks import run_hired_agent
        run_hired_agent.delay(hired_agent_id=str(agent.id))
        return Response({"queued": True})


class AgentInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        qs = AgentInsight.objects.filter(hired_agent=agent)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        data = AgentInsightSerializer(page if page is not None else qs, many=True).data
        return paginator.get_paginated_response(data) if page is not None else Response(data)


class AgentChatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        msgs = AgentMessage.objects.filter(hired_agent=agent)[:100]
        return Response({"data": AgentMessageSerializer(msgs, many=True).data})

    def post(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        text = (request.data.get("message") or "").strip()
        if not text:
            return Response({"error": "message is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        from apps.agents.services.chat import handle_user_message
        reply = handle_user_message(agent, text, channel="in_app")
        return Response(AgentMessageSerializer(reply).data, status=status.HTTP_201_CREATED)


class AgentActionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, hired_id):
        agent = _get_hired(request.user, hired_id)
        qs = AgentAction.objects.filter(hired_agent=agent)
        return Response({"data": AgentActionSerializer(qs, many=True).data})


class AgentActionDecisionView(APIView):
    """POST /actions/<id>/<decision>/ where decision is approve|reject."""

    permission_classes = [IsAuthenticated]

    def post(self, request, action_id, decision):
        try:
            action = AgentAction.objects.select_related("hired_agent").get(
                id=action_id, hired_agent__user=request.user
            )
        except AgentAction.DoesNotExist:
            raise ResourceNotFound("Action not found.") from None

        if action.status != AgentAction.STATUS_PROPOSED:
            return Response({"error": f"Action already {action.status}."},
                            status=status.HTTP_409_CONFLICT)

        if decision == "approve":
            action.status = AgentAction.STATUS_APPROVED
            action.approved_by = request.user
            action.save(update_fields=["status", "approved_by", "updated_at"])
            from apps.agents.tasks import execute_agent_action
            execute_agent_action.delay(action_id=str(action.id))
        elif decision == "reject":
            action.status = AgentAction.STATUS_REJECTED
            action.save(update_fields=["status", "updated_at"])
        else:
            return Response({"error": "decision must be approve or reject"},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(AgentActionSerializer(action).data)
