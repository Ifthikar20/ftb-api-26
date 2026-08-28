from rest_framework import serializers

from apps.assistant.models import AssistantConversation, AssistantMessage


class HistoryTurnSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    # Do not strip: preserve the exact prior text for context.
    content = serializers.CharField(
        allow_blank=True, trim_whitespace=False, max_length=8000,
    )


class AssistantAskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=4000)
    history = HistoryTurnSerializer(many=True, required=False, default=list)
    # When present, the turn is persisted into that thread and history is
    # read from the database rather than from the client. Omit it to have
    # the server open a new conversation and return its id.
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = ["id", "role", "content", "grounded", "created_at"]


class ConversationSummarySerializer(serializers.ModelSerializer):
    """Row shape for the sidebar list -- no message bodies."""

    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AssistantConversation
        fields = [
            "id", "title", "message_count",
            "last_message_at", "created_at", "updated_at",
        ]


class ConversationDetailSerializer(ConversationSummarySerializer):
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta(ConversationSummarySerializer.Meta):
        fields = [*ConversationSummarySerializer.Meta.fields, "messages"]


class ConversationRenameSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, allow_blank=True)
