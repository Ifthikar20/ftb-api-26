from rest_framework import serializers

from apps.voice_agent.models import (
    AgentConfig,
    AgentContextDocument,
    CalendarEvent,
    CallbackReminder,
    CallCampaign,
    CallExtraction,
    CallLog,
    CallTarget,
    CallTodo,
    DoNotCallEntry,
    PhoneNumber,
)


class AgentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentConfig
        fields = [
            "id", "is_active", "retell_agent_id", "phone_number",
            "forwarding_number", "greeting_message", "system_prompt",
            "business_context", "business_name",
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
            "is_possible_lead", "lead_score", "lead_signals",
            "lead_promoted_at", "lead_dismissed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "direction", "status", "duration_seconds", "duration_display",
            "started_at", "ended_at", "transcript", "summary", "sentiment",
            "extracted_data", "call_intent", "lead_name", "lead_id",
            "is_possible_lead", "lead_score", "lead_signals",
            "lead_promoted_at", "lead_dismissed_at",
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


class PhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = [
            "id", "number", "label", "provider", "is_active",
            "forwarded_to_agent", "telnyx_trunk_id", "livekit_outbound_trunk_id",
            "is_verified", "verified_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "livekit_outbound_trunk_id",
            "is_verified", "verified_at",
            "created_at", "updated_at",
        ]


class CallTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallTarget
        fields = [
            "id", "phone", "name", "metadata", "status",
            "attempt_count", "max_attempts", "last_attempt_at", "last_error",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "attempt_count", "last_attempt_at", "last_error",
            "created_at", "updated_at",
        ]


class CallCampaignSerializer(serializers.ModelSerializer):
    target_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    failed_count = serializers.SerializerMethodField()
    from_number_display = serializers.CharField(
        source="from_number.number", read_only=True
    )

    class Meta:
        model = CallCampaign
        fields = [
            "id", "name", "welcome_message", "from_number", "from_number_display",
            "status", "max_concurrent_calls", "calls_per_minute",
            "respect_business_hours", "created_by",
            "target_count", "pending_count", "completed_count", "failed_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "created_by", "from_number_display",
            "target_count", "pending_count", "completed_count", "failed_count",
            "created_at", "updated_at",
        ]

    def _count(self, obj, status=None):
        qs = obj.targets.all()
        if status:
            qs = qs.filter(status=status)
        return qs.count()

    def get_target_count(self, obj):
        return self._count(obj)

    def get_pending_count(self, obj):
        return self._count(obj, CallTarget.STATUS_PENDING)

    def get_completed_count(self, obj):
        return self._count(obj, CallTarget.STATUS_COMPLETED)

    def get_failed_count(self, obj):
        return self._count(obj, CallTarget.STATUS_FAILED)


class DoNotCallEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoNotCallEntry
        fields = ["id", "phone", "reason", "added_by", "created_at"]
        read_only_fields = ["id", "added_by", "created_at"]


class AgentContextDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentContextDocument
        fields = [
            "id", "title", "content", "is_active", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


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
