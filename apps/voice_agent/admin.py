from django.contrib import admin

from apps.voice_agent.models import (
    AgentConfig,
    CalendarEvent,
    CallbackReminder,
    CallExtraction,
    CallLog,
    CallTodo,
)


@admin.register(AgentConfig)
class AgentConfigAdmin(admin.ModelAdmin):
    list_display = ("website", "is_active", "phone_number", "business_name", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("website__name", "business_name", "phone_number")


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "website", "direction", "status", "caller_phone", "caller_name",
        "duration_seconds", "call_intent", "created_at",
    )
    list_filter = ("status", "direction", "sentiment")
    search_fields = ("caller_phone", "caller_name", "caller_email", "summary")
    readonly_fields = ("id", "external_call_id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "id", "website", "title", "status", "attendee_name", "attendee_phone",
        "start_time", "end_time", "assigned_to",
    )
    list_filter = ("status",)
    search_fields = ("title", "attendee_name", "attendee_phone", "attendee_email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("start_time",)


@admin.register(CallbackReminder)
class CallbackReminderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "website", "contact_name", "contact_phone", "remind_at",
        "status", "assigned_to",
    )
    list_filter = ("status",)
    search_fields = ("contact_name", "contact_phone")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("remind_at",)


@admin.register(CallExtraction)
class CallExtractionAdmin(admin.ModelAdmin):
    list_display = ("call_log", "call_category", "sentiment", "model_used", "processing_time_ms", "created_at")
    list_filter = ("call_category", "sentiment")
    readonly_fields = ("call_log", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(CallTodo)
class CallTodoAdmin(admin.ModelAdmin):
    list_display = ("id", "website", "description", "priority", "status", "assigned_to", "due_date", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("description",)
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
