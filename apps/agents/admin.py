from django.contrib import admin
from apps.agents.models import AgentRun, AgentStep


class AgentStepInline(admin.TabularInline):
    model = AgentStep
    extra = 0
    readonly_fields = [
        "step_number", "reasoning", "tool_name", "tool_params",
        "tool_result", "status", "tokens_used", "duration_ms",
    ]


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ["id", "website", "agent_type", "status", "trigger", "steps_count", "created_at"]
    list_filter = ["agent_type", "status", "trigger"]
    search_fields = ["website__name", "summary"]
    readonly_fields = [
        "id", "website", "user", "agent_type", "status", "trigger",
        "context", "summary", "findings", "approval_request",
        "approved_at", "approved_by", "steps_count", "total_tokens",
        "duration_ms", "started_at", "completed_at", "error_message",
    ]
    inlines = [AgentStepInline]
