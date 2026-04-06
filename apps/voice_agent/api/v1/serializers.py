from rest_framework import serializers

from apps.voice_agent.models import (
    AgentConfig,
    CalendarEvent,
    CallbackReminder,
    CallExtraction,
    CallLog,
    CallTodo,
)


class AgentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentConfig
        fields = [
            "id", "is_active", "retell_agent_id", "phone_number",
            "greeting_message", "system_prompt", "business_name",
            "business_hours", "appointment_duration_minutes", "timezone",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "retell_agent_id", "created_at", "updated_at"]


class CallLogSerializer(serializers.ModelSerializer):
    duration_display = serializers.CharField(read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True, default="")
    lead_id = serializers.UUIDField(source="lead.id", read_only=True, default=None)

    class Meta:
        model = CallLog
        fields = [
            "id", "direction", "status", "caller_phone", "caller_name",
            "caller_email", "caller_company", "duration_seconds", "duration_display",
            "started_at", "ended_at", "transcript", "summary", "sentiment",
            "extracted_data", "call_intent", "lead_name", "lead_id",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "direction", "status", "duration_seconds", "duration_display",
            "started_at", "ended_at", "transcript", "summary", "sentiment",
            "extracted_data", "call_intent", "lead_name", "lead_id",
            "created_at", "updated_at",
        ]


class CalendarEventSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=""
    )
    call_caller_phone = serializers.CharField(
        source="call_log.caller_phone", read_only=True, default=""
    )

    class Meta:
        model = CalendarEvent
        fields = [
            "id", "title", "description", "status", "start_time", "end_time",
            "timezone", "attendee_name", "attendee_phone", "attendee_email",
            "google_event_id", "outlook_event_id", "assigned_to", "assigned_to_name",
            "call_caller_phone", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "google_event_id", "outlook_event_id",
            "assigned_to_name", "call_caller_phone", "created_at", "updated_at",
        ]


class CallbackReminderSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=""
    )
    call_summary = serializers.CharField(
        source="call_log.summary", read_only=True, default=""
    )

    class Meta:
        model = CallbackReminder
        fields = [
            "id", "contact_name", "contact_phone", "reason", "remind_at",
            "status", "assigned_to", "assigned_to_name", "notes",
            "call_summary", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "assigned_to_name", "call_summary", "created_at", "updated_at",
        ]


class CallTodoSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=""
    )
    call_caller_name = serializers.CharField(
        source="call_log.caller_name", read_only=True, default=""
    )
    call_caller_phone = serializers.CharField(
        source="call_log.caller_phone", read_only=True, default=""
    )

    class Meta:
        model = CallTodo
        fields = [
            "id", "description", "priority", "status", "assigned_to",
            "assigned_to_name", "due_date", "completed_at",
            "call_caller_name", "call_caller_phone",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "assigned_to_name", "completed_at",
            "call_caller_name", "call_caller_phone",
            "created_at", "updated_at",
        ]


class CallExtractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallExtraction
        fields = [
            "id", "caller_info", "call_summary", "call_category",
            "sentiment", "follow_ups", "appointments_detected",
            "model_used", "processing_time_ms", "created_at",
        ]
        read_only_fields = [
            "id", "caller_info", "call_summary", "call_category",
            "sentiment", "follow_ups", "appointments_detected",
            "model_used", "processing_time_ms", "created_at",
        ]
