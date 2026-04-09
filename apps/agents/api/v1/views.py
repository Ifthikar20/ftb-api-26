from rest_framework import status
from rest_framework.response import Response

from apps.agents.agent_types import get_agent_config, get_available_agent_types
from apps.agents.api.v1.serializers import AgentRunListSerializer, AgentRunSerializer
from apps.agents.models import AgentRun
from core.interceptors.throttling import AIGenerationThrottle
from core.views import TenantScopedAPIView


class AgentTypesView(TenantScopedAPIView):
    """List all available agent types. Not website-scoped, but still authed."""

    def get(self, request):
        return Response(get_available_agent_types())


class AgentRunsView(TenantScopedAPIView):
    """List agent runs for a website, or trigger a new one."""

    def get(self, request, website_id):
        self.get_website(website_id)
        runs = AgentRun.objects.filter(website_id=website_id).select_related("website")[:50]
        return Response(AgentRunListSerializer(runs, many=True).data)

    def post(self, request, website_id):
        website = self.get_website(website_id)
        agent_type = request.data.get("agent_type")

        if not agent_type:
            return Response(
                {"error": "agent_type is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            config = get_agent_config(agent_type)
        except ValueError:
            return Response(
                {"error": f"Unknown agent type: {agent_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Don't allow duplicate running agents
        existing = AgentRun.objects.filter(
            website=website,
            agent_type=agent_type,
            status__in=["pending", "running"],
        ).exists()
        if existing:
            return Response(
                {"error": f"A {config['name']} agent is already running for this website."},
                status=status.HTTP_409_CONFLICT,
            )

        agent_run = AgentRun.objects.create(
            website=website,
            user=request.user,
            agent_type=agent_type,
            trigger="manual",
            requires_approval=config.get("requires_approval", False),
        )

        from apps.agents.tasks import run_agent_task
        run_agent_task.delay(str(agent_run.id))

        return Response(
            AgentRunSerializer(agent_run).data,
            status=status.HTTP_202_ACCEPTED,
        )


class AgentRunDetailView(TenantScopedAPIView):
    """Get detail for a specific agent run."""

    def get(self, request, website_id, run_id):
        self.get_website(website_id)
        run = self.get_tenant_object(
            AgentRun.objects.prefetch_related("steps"),
            id=run_id,
            website_id=website_id,
        )
        return Response(AgentRunSerializer(run).data)


class AgentRunApproveView(TenantScopedAPIView):
    """Approve a paused agent run."""

    throttle_classes = [AIGenerationThrottle]

    def post(self, request, website_id, run_id):
        self.get_website(website_id)
        run = self.get_tenant_object(
            AgentRun.objects.all(), id=run_id, website_id=website_id
        )

        if run.status != "paused":
            return Response(
                {"error": "Agent is not awaiting approval"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run.approved_by = request.user
        run.save(update_fields=["approved_by"])

        from apps.agents.tasks import resume_agent_task
        resume_agent_task.delay(str(run.id))

        return Response({"message": "Agent approved and resuming."}, status=status.HTTP_202_ACCEPTED)


class AgentRunCancelView(TenantScopedAPIView):
    """Cancel a running or paused agent run."""

    def post(self, request, website_id, run_id):
        self.get_website(website_id)
        run = self.get_tenant_object(
            AgentRun.objects.all(), id=run_id, website_id=website_id
        )

        if run.status not in ("pending", "running", "paused"):
            return Response(
                {"error": "Agent cannot be cancelled in its current state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run.status = "cancelled"
        run.save(update_fields=["status", "updated_at"])
        return Response({"message": "Agent cancelled."})


class AgentActivityView(TenantScopedAPIView):
    """Cross-website agent activity feed for the current user. Not website-scoped."""

    def get(self, request):
        runs = (
            AgentRun.objects
            .filter(website__user=request.user)
            .select_related("website")
            .order_by("-created_at")[:20]
        )
        return Response(AgentRunListSerializer(runs, many=True).data)
