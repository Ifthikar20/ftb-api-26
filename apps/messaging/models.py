import uuid

from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin


class Channel(TimestampMixin):
    """A connected messaging channel (Instagram, WhatsApp, Messenger, Web Chat)."""

    CHANNEL_TYPES = [
        ("instagram", "Instagram DM"),
        ("whatsapp", "WhatsApp"),
        ("messenger", "Facebook Messenger"),
        ("webchat", "Web Chat"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="messaging_channels"
    )
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    name = models.CharField(max_length=120, blank=True)
    access_token = models.TextField(blank=True, help_text="OAuth or API token for the channel")
    page_id = models.CharField(max_length=120, blank=True, help_text="Facebook Page ID / IG Business ID")
    phone_number = models.CharField(max_length=20, blank=True, help_text="WhatsApp phone number")
    webhook_secret = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["website", "channel_type"]

    def __str__(self):
        return f"{self.get_channel_type_display()} – {self.website}"


class Contact(TimestampMixin):
    """A person who has messaged the business on any channel."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="messaging_contacts"
    )
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="contacts")
    external_id = models.CharField(max_length=255, help_text="Platform-specific user ID")
    name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    tags = models.JSONField(default=list, blank=True)
    ai_summary = models.TextField(blank=True, help_text="AI-generated summary of this contact")
    lead_score = models.IntegerField(default=0, help_text="0-100 lead quality score")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ["channel", "external_id"]

    def __str__(self):
        return self.name or self.external_id


class Conversation(TimestampMixin):
    """A message thread between a contact and the business."""

    STATUS_CHOICES = [
        ("open", "Open"),
        ("snoozed", "Snoozed"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="conversations")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="conversations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_conversations"
    )
    ai_enabled = models.BooleanField(default=True, help_text="Whether AI auto-reply is active")
    subject = models.CharField(max_length=200, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=200, blank=True)
    unread_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-last_message_at"]

    def __str__(self):
        return f"Conversation with {self.contact} on {self.channel}"


class Message(TimestampMixin):
    """A single message in a conversation."""

    DIRECTION_CHOICES = [
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    ]

    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("image", "Image"),
        ("voice", "Voice Note"),
        ("file", "File"),
        ("template", "Template"),
    ]

    SENDER_TYPE_CHOICES = [
        ("human", "Human"),
        ("ai", "AI Agent"),
        ("system", "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default="text")
    content = models.TextField()
    media_url = models.URLField(blank=True)
    sent_by = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES, default="human")
    sent_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sent_messages"
    )
    external_id = models.CharField(max_length=255, blank=True, help_text="Platform message ID")
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_direction_display()} – {self.content[:60]}"


class AgentTrainingDoc(TimestampMixin):
    """A markdown training document for the messaging AI agent.

    Users create .md files to train the agent on products, tone, objection
    handling, scripts, and FAQs.  All active docs are concatenated into the
    system prompt when generating AI replies.
    """

    DOC_TYPES = [
        ("persona", "Persona & Tone"),
        ("product", "Product Knowledge"),
        ("rules", "Rules & Objections"),
        ("script", "Sales Script"),
        ("faq", "FAQ"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="agent_training_docs"
    )
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, default="custom")
    content = models.TextField(help_text="Markdown content the AI agent uses as training context")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()}) – {self.website}"


class AIInstruction(TimestampMixin):
    """Agent configuration — tone, feature flags, and legacy instruction text."""

    TONE_CHOICES = [
        ("professional", "Professional"),
        ("friendly", "Friendly"),
        ("casual", "Casual"),
        ("assertive", "Assertive"),
        ("bargaining", "Bargaining"),
        ("empathetic", "Empathetic"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    website = models.ForeignKey(
        "websites.Website", on_delete=models.CASCADE, related_name="ai_instructions"
    )
    name = models.CharField(max_length=120, default="Default Agent")
    instruction_text = models.TextField(
        blank=True,
        help_text="Legacy instruction text. Prefer AgentTrainingDoc for new content.",
    )
    personality = models.CharField(
        max_length=30, choices=TONE_CHOICES, default="professional",
        help_text="Active tone the AI agent uses when responding",
    )
    product_context = models.TextField(
        blank=True,
        help_text="Legacy product context. Prefer AgentTrainingDoc for new content.",
    )
    booking_enabled = models.BooleanField(
        default=False, help_text="Whether the AI can book appointments in chat"
    )
    auto_qualify = models.BooleanField(
        default=True, help_text="Whether the AI should score/qualify leads"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} – {self.website}"
