from rest_framework import serializers

from apps.agents.models import AgentRun, AgentStep


class AgentStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentStep
        fields = [
            "id", "step_number", "reasoning", "tool_name", "tool_params",
            "tool_result", "status", "error_message", "tokens_used",
            "duration_ms", "created_at",
        ]
        read_only_fields = fields


class AgentRunSerializer(serializers.ModelSerializer):
    steps = AgentStepSerializer(many=True, read_only=True)
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    website_name = serializers.CharField(source="website.name", read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id", "website", "website_name", "agent_type", "agent_type_display",
            "status", "status_display", "trigger", "summary", "findings",
            "requires_approval", "approval_request", "approved_at",
            "steps_count", "total_tokens", "duration_ms",
            "started_at", "completed_at", "error_message",
            "created_at", "updated_at", "steps",
        ]
        read_only_fields = fields


class AgentRunListSerializer(serializers.ModelSerializer):
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    website_name = serializers.CharField(source="website.name", read_only=True)

    class Meta:
        model = AgentRun
        fields = [
            "id", "website", "website_name", "agent_type", "agent_type_display",
            "status", "status_display", "trigger", "summary",
            "steps_count", "total_tokens", "duration_ms",
            "started_at", "completed_at", "created_at",
        ]
        read_only_fields = fields
