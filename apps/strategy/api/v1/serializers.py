from rest_framework import serializers
from apps.strategy.models import Strategy, Action, ContentCalendarEntry, ChatMessage, MorningBrief


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = [
            "id", "title", "description", "action_type", "estimated_impact",
            "estimated_time_minutes", "due_date", "status", "completed_at",
            "ai_reasoning", "week_number",
        ]
        read_only_fields = ["id", "completed_at"]


class StrategySerializer(serializers.ModelSerializer):
    actions = ActionSerializer(many=True, read_only=True)

    class Meta:
        model = Strategy
        fields = [
            "id", "plan_type", "generated_at", "status", "completion_pct",
            "summary", "actions",
        ]
        read_only_fields = fields


class StrategyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Strategy
        fields = ["id", "plan_type", "generated_at", "status", "completion_pct", "summary"]


class ContentCalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentCalendarEntry
        fields = [
            "id", "title", "topic", "content_type", "scheduled_date",
            "status", "ai_generated", "notes",
        ]
        read_only_fields = ["id", "ai_generated"]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = fields


class MorningBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = MorningBrief
        fields = ["id", "date", "content", "metrics_snapshot", "created_at"]
        read_only_fields = fields
