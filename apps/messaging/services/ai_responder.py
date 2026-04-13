"""AI Responder service — uses Anthropic Claude to generate conversational sales replies."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def build_system_prompt(instruction, contact):
    """Build the system prompt from AI instruction + contact context."""
    personality_map = {
        "professional": "You are a professional, courteous sales agent.",
        "friendly": "You are a warm, friendly sales agent who builds rapport quickly.",
        "casual": "You are a relaxed, casual sales agent. Keep it chill but helpful.",
        "assertive": "You are a confident, assertive closer. Be direct and persuasive.",
    }

    tone = personality_map.get(instruction.personality, personality_map["professional"])

    prompt = f"""{tone}

INSTRUCTIONS:
{instruction.instruction_text}

PRODUCT / SERVICE CONTEXT:
{instruction.product_context or "No specific product context provided."}

CONTACT INFO:
- Name: {contact.name or "Unknown"}
- Lead Score: {contact.lead_score}/100
- Tags: {', '.join(contact.tags) if contact.tags else 'None'}
- AI Summary: {contact.ai_summary or 'New contact, no history yet.'}

RULES:
1. Keep responses concise (1-3 sentences max unless explaining something complex).
2. Always be helpful and move the conversation toward a conversion goal.
3. If the person asks about pricing, provide it if available in the product context.
4. If they express interest in booking, suggest a time or ask for their availability.
5. Never reveal that you are an AI unless directly asked.
6. Mirror the customer's communication style (formal/casual).
7. If you don't know something, say you'll check and get back to them.
"""

    if instruction.auto_qualify:
        prompt += """
LEAD QUALIFICATION:
- Assess buying intent on every message (low/medium/high).
- Look for: budget mentions, timeline, decision authority, specific needs.
- Internally track qualification but don't make it obvious to the contact.
"""

    if instruction.booking_enabled:
        prompt += """
APPOINTMENT BOOKING:
- If the contact wants to schedule a call/meeting, offer available times.
- Confirm the booking details (date, time, topic).
- Be proactive about suggesting meetings when interest is high.
"""

    return prompt


def generate_ai_reply(conversation, instruction=None):
    """Generate an AI reply for a conversation using Claude."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return None

    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not configured")
        return None

    if instruction is None:
        instruction = conversation.channel.website.ai_instructions.filter(
            is_active=True
        ).first()

    if not instruction:
        logger.warning("No active AI instruction found for website %s", conversation.channel.website)
        return None

    # Build message history
    messages = []
    for msg in conversation.messages.order_by("created_at").select_related()[:50]:
        role = "user" if msg.direction == "inbound" else "assistant"
        messages.append({"role": role, "content": msg.content})

    if not messages:
        return None

    system_prompt = build_system_prompt(instruction, conversation.contact)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=system_prompt,
            messages=messages,
        )
        # Track AI token usage
        try:
            from core.ai_tracking import record_usage
            record_usage(
                module="messaging", model_name="claude-sonnet-4-20250514",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        except Exception:
            pass
        return response.content[0].text
    except Exception as e:
        logger.exception("AI reply generation failed: %s", e)
        return None
