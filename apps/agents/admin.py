from django.contrib import admin

from apps.agents.models import AgentAction, AgentInsight, AgentMessage, HiredAgent


@admin.register(HiredAgent)
class HiredAgentAdmin(admin.ModelAdmin):
    list_display = ("agent_key", "website", "user", "is_active", "frequency", "next_run_at")
    list_filter = ("is_active", "frequency", "agent_key")
    search_fields = ("agent_key", "website__name", "user__email")


@admin.register(AgentInsight)
class AgentInsightAdmin(admin.ModelAdmin):
    list_display = ("title", "hired_agent", "run_date", "created_at")
    list_filter = ("run_date",)


@admin.register(AgentAction)
class AgentActionAdmin(admin.ModelAdmin):
    list_display = ("action_type", "hired_agent", "status", "created_at")
    list_filter = ("status", "action_type")


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ("hired_agent", "role", "channel", "created_at")
    list_filter = ("role", "channel")
