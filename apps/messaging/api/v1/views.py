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
            {"name": "Sarah Mitchell", "email": "sarah@innovateagency.com", "lead_score": 35,
             "tags": ["subscriber", "agency"], "ai_summary": "Subscribed via landing page. Agency owner — initially skeptical but warming up after seeing services list."},
            {"name": "James Rodriguez", "email": "james@startupco.com", "lead_score": 55,
             "tags": ["subscriber", "startup"], "ai_summary": "Signed up for newsletter. Runs a SaaS startup. Concerned about budget but interested in SEO features."},
            {"name": "Emily Chen", "email": "emily@designstudio.io", "lead_score": 20,
             "tags": ["subscriber", "cold"], "ai_summary": "Subscribed from blog post. Small studio, low traffic. Not yet convinced of ROI."},
            {"name": "Michael Thompson", "email": "michael@bigcorp.com", "lead_score": 80,
             "tags": ["subscriber", "enterprise", "warm"], "ai_summary": "VP Marketing. Subscribed from webinar. High budget, actively evaluating platforms after seeing services breakdown."},
            {"name": "Priya Patel", "email": "priya@ecomstore.com", "lead_score": 60,
             "tags": ["subscriber", "ecommerce"], "ai_summary": "Subscribed from ad. E-commerce brand spending $20K/mo on ads. Interested in attribution after outreach."},
        ]

        demo_conversations = [
            # 1. Sarah — pushes back, you respond with services
            [
                ("outbound", "Hi Sarah! Thanks for subscribing to FetchBot 🙌 I noticed you run an agency — I'd love to show you how our platform can help you manage analytics and leads across all your clients' websites."),
                ("inbound", "Thanks for reaching out, but we already have tools in place. Google Analytics and a basic CRM handle most of what we need. Not sure we need another platform."),
                ("outbound", "I totally understand — most agencies start there! But here's what sets FetchBot apart: we combine everything into one dashboard. Here's what you get:\n\n📊 Real-time analytics with AI-powered insights\n🎯 AI Lead Scoring — automatically rank visitors by purchase intent\n🔍 SEO Keyword Intelligence — track rankings across Google + AI search engines\n🤖 AI Agents — automated research assistants that run 24/7\n📞 Voice Agent — AI-powered calls for lead qualification\n🔥 Heatmaps — see exactly where visitors click\n📈 LLM Ranking — check if AI assistants mention your clients' brands\n\nWould any of these help fill a gap in your current stack?"),
                ("inbound", "Actually the AI Lead Scoring and LLM Ranking sound interesting. We've been struggling to figure out which website visitors are actually worth following up on."),
                ("outbound", "That's exactly the problem we solve! Our AI scores every visitor in real-time and flags the hot ones. Want me to set up a quick 15-min demo this week?"),
            ],
            # 2. James — budget concern, you address it
            [
                ("outbound", "Hey James! Welcome to FetchBot 🚀 Saw you signed up from our startup growth blog. What are you building?"),
                ("inbound", "Hey, yeah I'm running a SaaS startup. We're still early stage so honestly we can't afford expensive marketing tools right now. Just browsing."),
                ("outbound", "Totally get it — budget is everything at early stage. That's actually why a lot of startups choose us over cobbling together 5 different tools. With FetchBot you get:\n\n✅ Website Analytics (replace GA)\n✅ AI Lead Finder (finds prospects automatically)\n✅ SEO Keyword Tracking (monitor your rankings)\n✅ AI Sales Agents (automated outreach)\n✅ Heatmaps + Conversion Optimization\n\nAll in one platform, starting at $49/month. That's cheaper than running Hotjar + Ahrefs + a CRM separately. Would you want to try the free trial?"),
                ("inbound", "Hmm $49/mo isn't bad. Let me think about it. The AI Lead Finder is interesting — does it actually work?"),
            ],
            # 3. Emily — not convinced, short conversation
            [
                ("outbound", "Hi Emily! Thanks for subscribing to FetchBot 😊 Noticed you're in the design space — we help creative studios attract more clients through AI-powered marketing intelligence."),
                ("inbound", "Hi, honestly I don't think we need this. We're a small studio with only about 200 visitors a month. These enterprise tools aren't really built for us."),
                ("outbound", "I hear you — and actually, that's exactly why smaller studios use us! Even with 200 visitors, our AI can:\n\n• Score every visitor so you know who's a real potential client\n• Track which pages convert best\n• Find new leads in your niche automatically\n• Show you a heatmap of what visitors click on\n\nSmall studios often get the biggest ROI because every lead counts. Would you be open to a 10-minute walkthrough?"),
            ],
            # 4. Michael — enterprise, converts quickly
            [
                ("outbound", "Hi Michael! Thanks for attending our webinar on AI-powered marketing. I'd love to learn more about what you're looking for at BigCorp."),
                ("inbound", "Hi, the webinar was great. We're evaluating marketing intelligence platforms but we need something that handles enterprise scale. What exactly do you offer?"),
                ("outbound", "Great question! Here's the full FetchBot platform overview:\n\n🔹 Real-time Analytics Dashboard — visitor tracking, traffic sources, page performance\n🔹 AI Lead Scoring & Finder — automatically discover and rank leads\n🔹 SEO Keyword Intelligence — position tracking + AI search visibility\n🔹 LLM Ranking Checker — see how AI assistants (ChatGPT, Claude, Gemini) talk about your brand\n🔹 AI Agents — autonomous research bots that gather competitive intel\n🔹 Voice Agent — AI phone calls for lead qualification\n🔹 Heatmaps & Click Tracking — visual UX insights\n🔹 Messaging Hub — AI-powered sales conversations across channels\n🔹 Campaign Management — track all your marketing campaigns\n\nFor enterprise, we also offer: SSO, custom SLAs, dedicated account manager, API access, and white-label options."),
                ("inbound", "That's comprehensive. Our budget is around $10-15K/month. We need enterprise SLAs and a dedicated account manager. Can we do a call this week?"),
                ("outbound", "Absolutely! I've got availability Thursday at 2pm EST or Friday at 10am EST. Which works better? I'll bring our enterprise team on the call. 🎯"),
                ("inbound", "Thursday 2pm works. Looking forward to it."),
            ],
            # 5. Priya — ad attribution pain point
            [
                ("outbound", "Hi Priya! Thanks for signing up for FetchBot. Noticed you're in e-commerce — how's your ad performance tracking going?"),
                ("inbound", "Honestly, not great. We spend about $20K/month on Facebook and TikTok ads and we have almost no visibility into which campaigns actually drive sales. Our attribution is a mess."),
                ("outbound", "That's a really common pain point — and exactly what FetchBot solves. Here's what we can do for you:\n\n📊 Multi-touch attribution across Facebook, TikTok, Google\n🎯 AI Lead Scoring — know which ad-driven visitors are most likely to buy\n🔍 Conversion tracking with our lightweight pixel\n📈 Campaign ROI dashboards — see cost-per-lead by channel\n🤖 AI Agents that analyze your top-performing ads and suggest optimizations\n\nWe've helped e-commerce brands cut wasted ad spend by 30-40%. Want me to show you how it works with a quick demo?"),
                ("inbound", "Yes, definitely. Cutting even 20% waste would save us $4K/month. When can we talk?"),
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
