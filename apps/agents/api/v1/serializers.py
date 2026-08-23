"""DRF serializers for the agents REST surface."""
from __future__ import annotations

from rest_framework import serializers

from apps.agents.catalog import get_spec
from apps.agents.models import AgentAction, AgentInsight, AgentMessage, HiredAgent


def _spec_meta(agent_key: str) -> dict:
    spec = get_spec(agent_key)
    if spec is None:
        return {"key": agent_key, "name": agent_key, "tagline": "", "icon": "Bot"}
    return {
        "key": spec.key, "name": spec.name, "tagline": spec.tagline,
        "domain": spec.domain, "icon": spec.icon,
        "allowed_action_types": spec.allowed_action_types,
    }


class HiredAgentSerializer(serializers.ModelSerializer):
    spec = serializers.SerializerMethodField()
    website_name = serializers.CharField(source="website.name", read_only=True)

    class Meta:
        model = HiredAgent
        fields = (
            "id", "agent_key", "spec", "website", "website_name", "is_active",
            "frequency", "schedule_time", "slack_connection", "config",
            "next_run_at", "last_run_at", "consecutive_failures", "created_at",
        )
        # ``website`` and ``agent_key`` are the identity of the hire and are
        # set only at creation (HireAgentView, with WebsiteService.get_for_user
        # ownership checks). They MUST stay read-only here: without this, a
        # PATCH could repoint an agent at another tenant's website (IDOR) and
        # read that tenant's data back through AgentInsightsView.
        read_only_fields = (
            "id", "agent_key", "website", "next_run_at", "last_run_at",
            "consecutive_failures", "created_at",
        )

    def get_spec(self, obj):
        return _spec_meta(obj.agent_key)

    def validate_slack_connection(self, value):
        """Reject a slack_connection the requesting user does not own.

        ``slack_connection`` is intentionally editable, but the default
        PrimaryKeyRelatedField queryset spans all tenants, so ownership must
        be enforced explicitly here to prevent binding another tenant's
        IntegrationConnection.
        """
        if value is None:
            return value
        request = self.context.get("request")
        if request is None or value.user_id != request.user.id:
            # Generic message: do not disclose whether the id exists.
            raise serializers.ValidationError("Invalid Slack connection.")
        return value


class AgentInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentInsight
        fields = (
            "id", "hired_agent", "run_date", "title", "summary_markdown",
            "data", "source_refs", "delivered_channels", "cost_usd", "created_at",
        )


class AgentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentAction
        fields = (
            "id", "hired_agent", "insight", "action_type", "title", "params",
            "status", "executed_at", "result", "created_at",
        )
        read_only_fields = ("status", "executed_at", "result", "created_at")


class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage
        fields = ("id", "role", "text", "channel", "created_at")
