from django.contrib import admin

from apps.messaging.models import AIInstruction, Channel, Contact, Conversation, Message


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["channel_type", "website", "is_active", "created_at"]
    list_filter = ["channel_type", "is_active"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "lead_score", "channel", "created_at"]
    list_filter = ["lead_score"]
    search_fields = ["name", "email"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["contact", "channel", "status", "ai_enabled", "last_message_at"]
    list_filter = ["status", "ai_enabled"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "direction", "sent_by", "content", "created_at"]
    list_filter = ["direction", "sent_by"]


@admin.register(AIInstruction)
class AIInstructionAdmin(admin.ModelAdmin):
    list_display = ["name", "website", "personality", "is_active", "created_at"]
    list_filter = ["personality", "is_active"]
