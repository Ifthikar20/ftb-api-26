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
        read_only_fields = (
            "id", "next_run_at", "last_run_at", "consecutive_failures", "created_at",
        )

    def get_spec(self, obj):
        return _spec_meta(obj.agent_key)


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
