from rest_framework import serializers


class HistoryTurnSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    # Do not strip: preserve the exact prior text for context.
    content = serializers.CharField(
        allow_blank=True, trim_whitespace=False, max_length=8000,
    )


class AssistantAskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=4000)
    history = HistoryTurnSerializer(many=True, required=False, default=list)
