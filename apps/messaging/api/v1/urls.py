from django.urls import path

from apps.messaging.api.v1.views import (
    AIInstructionDetailView,
    AIInstructionListCreateView,
    AIReplyView,
    ChannelListCreateView,
    ContactListView,
    ConversationDetailView,
    ConversationListView,
    SeedDemoDataView,
    SendMessageView,
)

urlpatterns = [
    # Channels
    path("<uuid:website_id>/channels/", ChannelListCreateView.as_view(), name="messaging-channels"),

    # Conversations
    path("<uuid:website_id>/conversations/", ConversationListView.as_view(), name="messaging-conversations"),
    path("<uuid:website_id>/conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="messaging-conversation-detail"),

    # Messages
    path("<uuid:website_id>/conversations/<uuid:conversation_id>/send/", SendMessageView.as_view(), name="messaging-send"),
    path("<uuid:website_id>/conversations/<uuid:conversation_id>/ai-reply/", AIReplyView.as_view(), name="messaging-ai-reply"),

    # Contacts
    path("<uuid:website_id>/contacts/", ContactListView.as_view(), name="messaging-contacts"),

    # AI Instructions
    path("<uuid:website_id>/instructions/", AIInstructionListCreateView.as_view(), name="messaging-instructions"),
    path("<uuid:website_id>/instructions/<uuid:instruction_id>/", AIInstructionDetailView.as_view(), name="messaging-instruction-detail"),

    # Demo
    path("<uuid:website_id>/seed-demo/", SeedDemoDataView.as_view(), name="messaging-seed-demo"),
]
