from rest_framework import serializers

from apps.messaging.models import AIInstruction, Channel, Contact, Conversation, Message


class ChannelSerializer(serializers.ModelSerializer):
    channel_type_display = serializers.CharField(source="get_channel_type_display", read_only=True)

    class Meta:
        model = Channel
        fields = [
            "id", "channel_type", "channel_type_display", "name",
            "page_id", "phone_number", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender_display = serializers.CharField(source="get_sent_by_display", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "direction", "message_type", "content", "media_url",
            "sent_by", "sender_display", "is_read", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ContactSerializer(serializers.ModelSerializer):
    channel_type = serializers.CharField(source="channel.channel_type", read_only=True)

    class Meta:
        model = Contact
        fields = [
            "id", "name", "avatar_url", "email", "phone", "tags",
            "ai_summary", "lead_score", "channel_type", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source="contact.name", read_only=True)
    contact_avatar = serializers.CharField(source="contact.avatar_url", read_only=True)
    channel_type = serializers.CharField(source="channel.channel_type", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id", "contact_name", "contact_avatar", "channel_type",
            "status", "ai_enabled", "last_message_at", "last_message_preview",
            "unread_count", "created_at",
        ]


class ConversationDetailSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    channel = ChannelSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id", "contact", "channel", "status", "ai_enabled",
            "last_message_at", "unread_count", "messages", "created_at",
        ]


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=Message.MESSAGE_TYPE_CHOICES, default="text"
    )


class AIInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInstruction
        fields = [
            "id", "name", "instruction_text", "personality",
            "product_context", "booking_enabled", "auto_qualify",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
