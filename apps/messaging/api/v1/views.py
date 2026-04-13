import logging
import uuid

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.messaging.models import AIInstruction, Channel, Contact, Conversation, Message
from apps.messaging.api.v1.serializers import (
    AIInstructionSerializer,
    ChannelSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    ContactSerializer,
    SendMessageSerializer,
)
from apps.messaging.services.ai_responder import generate_ai_reply

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────

def _get_website(request, website_id):
    """Get a website that belongs to the current user."""
    from apps.websites.models import Website
    return get_object_or_404(Website, id=website_id, user=request.user)


# ── Channel Views ────────────────────────────────────────────────

class ChannelListCreateView(generics.ListCreateAPIView):
    """List all channels for a website or create a new one."""
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        website = _get_website(self.request, self.kwargs["website_id"])
        return Channel.objects.filter(website=website)

    def perform_create(self, serializer):
        website = _get_website(self.request, self.kwargs["website_id"])
        serializer.save(website=website)


# ── Conversation Views ───────────────────────────────────────────

class ConversationListView(generics.ListAPIView):
    """List all conversations for a website with filters."""
    serializer_class = ConversationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        website = _get_website(self.request, self.kwargs["website_id"])
        qs = Conversation.objects.filter(
            channel__website=website
        ).select_related("contact", "channel")

        # Filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        channel_type = self.request.query_params.get("channel")
        if channel_type:
            qs = qs.filter(channel__channel_type=channel_type)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(contact__name__icontains=search)

        return qs


class ConversationDetailView(generics.RetrieveUpdateAPIView):
    """Get or update a single conversation (includes messages)."""
    serializer_class = ConversationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        website = _get_website(self.request, self.kwargs["website_id"])
        conv = get_object_or_404(
            Conversation.objects.select_related("contact", "channel").prefetch_related("messages"),
            id=self.kwargs["conversation_id"],
            channel__website=website,
        )
        # Mark as read
        conv.unread_count = 0
        conv.save(update_fields=["unread_count"])
        conv.messages.filter(direction="inbound", is_read=False).update(is_read=True)
        return conv


# ── Message Views ────────────────────────────────────────────────

class SendMessageView(APIView):
    """Send a message in a conversation (human or trigger AI reply)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, conversation_id):
        website = _get_website(request, website_id)
        conversation = get_object_or_404(
            Conversation, id=conversation_id, channel__website=website
        )

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create outbound message
        msg = Message.objects.create(
            conversation=conversation,
            direction="outbound",
            message_type=serializer.validated_data["message_type"],
            content=serializer.validated_data["content"],
            sent_by="human",
            sent_by_user=request.user,
        )

        # Update conversation
        conversation.last_message_at = timezone.now()
        conversation.last_message_preview = msg.content[:200]
        conversation.save(update_fields=["last_message_at", "last_message_preview"])

        from apps.messaging.api.v1.serializers import MessageSerializer
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class AIReplyView(APIView):
    """Generate an AI reply for a conversation."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, conversation_id):
        website = _get_website(request, website_id)
        conversation = get_object_or_404(
            Conversation.objects.select_related("contact", "channel"),
            id=conversation_id,
            channel__website=website,
        )

        reply_text = generate_ai_reply(conversation)
        if not reply_text:
            return Response(
                {"error": "Could not generate AI reply. Check AI instructions and API key."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create AI message
        msg = Message.objects.create(
            conversation=conversation,
            direction="outbound",
            message_type="text",
            content=reply_text,
            sent_by="ai",
        )

        # Update conversation
        conversation.last_message_at = timezone.now()
        conversation.last_message_preview = msg.content[:200]
        conversation.save(update_fields=["last_message_at", "last_message_preview"])

        from apps.messaging.api.v1.serializers import MessageSerializer
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


# ── Contact Views ────────────────────────────────────────────────

class ContactListView(generics.ListAPIView):
    """List all contacts for a website."""
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        website = _get_website(self.request, self.kwargs["website_id"])
        return Contact.objects.filter(website=website).select_related("channel")


# ── AI Instruction Views ─────────────────────────────────────────

class AIInstructionListCreateView(generics.ListCreateAPIView):
    """List or create AI instructions for a website."""
    serializer_class = AIInstructionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        website = _get_website(self.request, self.kwargs["website_id"])
        return AIInstruction.objects.filter(website=website)

    def perform_create(self, serializer):
        website = _get_website(self.request, self.kwargs["website_id"])
        serializer.save(website=website)


class AIInstructionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete an AI instruction."""
    serializer_class = AIInstructionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        website = _get_website(self.request, self.kwargs["website_id"])
        return get_object_or_404(
            AIInstruction, id=self.kwargs["instruction_id"], website=website
        )


# ── Demo Data ─────────────────────────────────────────────────────

class SeedDemoDataView(APIView):
    """Create demo conversations for testing the messaging UI."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = _get_website(request, website_id)

        # Create webchat channel
        channel, _ = Channel.objects.get_or_create(
            website=website, channel_type="webchat",
            defaults={"name": "Website Chat", "is_active": True},
        )

        demo_contacts = [
            {"name": "Sarah Mitchell", "email": "sarah@example.com", "lead_score": 85,
             "tags": ["hot-lead", "enterprise"], "ai_summary": "Interested in premium plan. Has a team of 15. Looking for analytics + voice agent."},
            {"name": "James Rodriguez", "email": "james@startupco.com", "lead_score": 62,
             "tags": ["startup", "seo"], "ai_summary": "Running an SEO agency with 40 clients. Needs keyword tracking at scale."},
            {"name": "Emily Chen", "email": "emily@designstudio.io", "lead_score": 45,
             "tags": ["design", "new-lead"], "ai_summary": "Small design studio, exploring lead gen options. Budget-conscious."},
            {"name": "Michael Thompson", "email": "michael@bigcorp.com", "lead_score": 92,
             "tags": ["enterprise", "decision-maker", "hot-lead"], "ai_summary": "VP of Marketing at BigCorp. Wants full platform demo. $10K+ budget."},
            {"name": "Priya Patel", "email": "priya@ecomstore.com", "lead_score": 70,
             "tags": ["ecommerce", "ads"], "ai_summary": "E-commerce brand doing $2M/yr. Needs ad attribution and lead scoring."},
        ]

        demo_conversations = [
            [
                ("inbound", "Hi! I saw your platform and I'm interested in the analytics features. Can you tell me more?"),
                ("outbound", "Hey Sarah! Thanks for reaching out 🙌 Absolutely — FetchBot gives you real-time visitor tracking, AI-powered lead scoring, and heatmaps. What size is your team?"),
                ("inbound", "We have about 15 people. We're currently using Google Analytics but want something more actionable."),
                ("outbound", "Perfect — our AI insights layer goes way beyond GA. It actually scores your visitors and predicts which ones are ready to buy. Want me to set up a demo?"),
                ("inbound", "Yes! That sounds great. Do you have availability this week?"),
            ],
            [
                ("inbound", "Hey, I run an SEO agency and need keyword tracking for about 40 clients. What's your pricing?"),
                ("outbound", "Hi James! We'd love to help. Our agency plan supports unlimited websites with keyword position tracking via DataForSEO. How many keywords per client are you tracking?"),
                ("inbound", "Around 50-100 per client. What would that cost?"),
            ],
            [
                ("inbound", "Hi there, just checking out your platform. Looks interesting but not sure if it's for us."),
                ("outbound", "Hey Emily! No worries — what kind of business are you running? I can tell you if FetchBot would be a good fit 😊"),
                ("inbound", "Small design studio, about 5 people. We don't get much web traffic honestly."),
            ],
            [
                ("inbound", "I'm the VP of Marketing at BigCorp. We need a full marketing intelligence stack—analytics, lead scoring, AI agents. Can we schedule a call?"),
                ("outbound", "Hi Michael! Great to hear from you. FetchBot is exactly what you're describing — we have analytics, AI lead scoring, voice agents, and keyword intelligence all in one platform."),
                ("inbound", "Excellent. Our budget is around $10-15K/month. We need enterprise SLAs and a dedicated account manager."),
                ("outbound", "Absolutely — we offer enterprise plans with SLAs, dedicated support, and custom onboarding. Let me get our enterprise team on a call with you. When works best?"),
                ("inbound", "Thursday afternoon works. 2pm EST?"),
                ("outbound", "Done! You're booked for Thursday at 2pm EST. I'll send a calendar invite shortly. Looking forward to it! 🎯"),
            ],
            [
                ("inbound", "Do you integrate with Facebook and TikTok for ad attribution?"),
                ("outbound", "Hey Priya! Yes, we have Facebook and TikTok pixel integrations for conversion tracking. We can show you exactly which ads are driving your best leads."),
                ("inbound", "That's exactly what I need. We're spending $20K/month on ads and have no idea what's working."),
            ],
        ]

        created = 0
        for i, contact_data in enumerate(demo_contacts):
            contact, _ = Contact.objects.get_or_create(
                channel=channel,
                external_id=f"demo-{contact_data['email']}",
                defaults={
                    "website": website,
                    "name": contact_data["name"],
                    "email": contact_data["email"],
                    "lead_score": contact_data["lead_score"],
                    "tags": contact_data["tags"],
                    "ai_summary": contact_data["ai_summary"],
                },
            )

            conv, conv_created = Conversation.objects.get_or_create(
                contact=contact,
                channel=channel,
                defaults={
                    "status": "open",
                    "ai_enabled": True,
                    "last_message_at": timezone.now(),
                },
            )

            if conv_created and i < len(demo_conversations):
                for direction, content in demo_conversations[i]:
                    msg = Message.objects.create(
                        conversation=conv,
                        direction=direction,
                        content=content,
                        sent_by="human" if direction == "inbound" else "ai",
                    )
                conv.last_message_preview = demo_conversations[i][-1][1][:200]
                conv.unread_count = 1 if demo_conversations[i][-1][0] == "inbound" else 0
                conv.save()
                created += 1

        # Create default AI instruction
        AIInstruction.objects.get_or_create(
            website=website,
            name="Default Sales Agent",
            defaults={
                "instruction_text": (
                    "You are a sales agent for FetchBot, an AI-powered marketing intelligence platform. "
                    "Your goal is to qualify leads, answer product questions, and book demo calls. "
                    "Be helpful, professional, and proactive."
                ),
                "personality": "friendly",
                "product_context": (
                    "FetchBot features: Real-time analytics, AI lead scoring, keyword tracking, "
                    "voice agents, LLM ranking checker, heatmaps, campaign management. "
                    "Plans: Starter ($49/mo), Pro ($149/mo), Enterprise (custom). "
                    "Key differentiator: All-in-one platform with AI-powered insights."
                ),
                "booking_enabled": True,
                "auto_qualify": True,
            },
        )

        return Response({"created": created, "message": f"Created {created} demo conversations"})
