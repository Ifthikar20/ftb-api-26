"""AI Responder service — composes system prompts from training docs and generates replies.

The system prompt is built by concatenating all active AgentTrainingDoc markdown
documents for the website, then prepending tone instructions and appending
contact context.  Every AI reply includes audit metadata so the frontend can
show which docs/tone/model were used.
"""

import logging
from dataclasses import dataclass, field

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Tone definitions ─────────────────────────────────────────────

TONE_PROMPTS = {
    "professional": (
        "You are a professional, courteous sales agent. "
        "Be precise, respectful, and solution-oriented."
    ),
    "friendly": (
        "You are a warm, friendly sales agent who builds rapport quickly. "
        "Use casual language and emoji sparingly to keep it human."
    ),
    "casual": (
        "You are a relaxed, casual sales agent. Keep it chill but helpful. "
        "Talk like a knowledgeable friend, not a corporate rep."
    ),
    "assertive": (
        "You are a confident, assertive closer. Be direct and persuasive. "
        "Push toward action but never be rude."
    ),
    "bargaining": (
        "You are a sharp negotiator and deal-maker. Your goal is to close deals. "
        "Acknowledge objections gracefully, reframe value, offer alternatives, "
        "and always steer toward a commitment. Use urgency tactfully. "
        "When price is mentioned, quantify ROI. Never give in immediately — "
        "counter with value before discussing discounts."
    ),
    "empathetic": (
        "You are an empathetic, understanding support agent. "
        "Listen first, acknowledge feelings, and solve problems gently. "
        "Prioritize the customer's comfort over speed."
    ),
}


@dataclass
class AIReplyResult:
    """Returned by generate_ai_reply with both the text and audit trail."""
    content: str
    audit: dict = field(default_factory=dict)


# ── Prompt builder ────────────────────────────────────────────────

def build_system_prompt(*, instruction, contact, training_docs):
    """Build the system prompt from tone + training docs + contact context.

    Args:
        instruction: AIInstruction instance (tone + feature flags)
        contact: Contact instance
        training_docs: queryset or list of AgentTrainingDoc instances

    Returns:
        (prompt_text, doc_titles) — the composed prompt and list of doc titles used
    """
    tone_key = instruction.personality if instruction else "professional"
    tone_preamble = TONE_PROMPTS.get(tone_key, TONE_PROMPTS["professional"])

    sections = [tone_preamble, ""]

    # ── Training documents (the .md knowledge base) ──
    doc_titles = []
    for doc in training_docs:
        sections.append(f"--- {doc.title} ---")
        sections.append(doc.content)
        sections.append("")
        doc_titles.append(doc.title)

    # ── Legacy fallback: if no training docs exist, use AIInstruction text fields ──
    if not doc_titles and instruction:
        if instruction.instruction_text:
            sections.append("--- Agent Instructions ---")
            sections.append(instruction.instruction_text)
            sections.append("")
        if instruction.product_context:
            sections.append("--- Product Context ---")
            sections.append(instruction.product_context)
            sections.append("")

    # ── Contact context ──
    sections.append("--- Current Contact ---")
    sections.append(f"- Name: {contact.name or 'Unknown'}")
    sections.append(f"- Lead Score: {contact.lead_score}/100")
    sections.append(f"- Tags: {', '.join(contact.tags) if contact.tags else 'None'}")
    sections.append(f"- AI Summary: {contact.ai_summary or 'New contact, no history yet.'}")
    sections.append("")

    # ── Global rules ──
    sections.append("--- Rules ---")
    sections.append("1. Keep responses concise (1–3 sentences max unless explaining something complex).")
    sections.append("2. Always be helpful and move the conversation toward a conversion goal.")
    sections.append("3. If the person asks about pricing, provide it if available in the training docs above.")
    sections.append("4. If they express interest in booking, suggest a time or ask for their availability.")
    sections.append("5. Never reveal that you are an AI unless directly asked.")
    sections.append("6. Mirror the customer's communication style (formal/casual).")
    sections.append("7. If you don't know something, say you'll check and get back to them.")

    if instruction and instruction.auto_qualify:
        sections.append("")
        sections.append("--- Lead Qualification ---")
        sections.append("- Assess buying intent on every message (low/medium/high).")
        sections.append("- Look for: budget mentions, timeline, decision authority, specific needs.")
        sections.append("- Internally track qualification but don't make it obvious to the contact.")

    if instruction and instruction.booking_enabled:
        sections.append("")
        sections.append("--- Appointment Booking ---")
        sections.append("- If the contact wants to schedule a call/meeting, offer available times.")
        sections.append("- Confirm the booking details (date, time, topic).")
        sections.append("- Be proactive about suggesting meetings when interest is high.")

    return "\n".join(sections), doc_titles


# ── Main entry point ──────────────────────────────────────────────

def generate_ai_reply(conversation, instruction=None):
    """Generate an AI reply for a conversation using Claude.

    Returns an AIReplyResult with the reply text and audit metadata,
    or None if generation fails.
    """
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return None

    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not configured")
        return None

    website = conversation.channel.website

    # Resolve agent config
    if instruction is None:
        instruction = website.ai_instructions.filter(is_active=True).first()

    # Load active training docs
    from apps.messaging.models import AgentTrainingDoc
    training_docs = list(
        AgentTrainingDoc.objects.filter(website=website, is_active=True)
        .order_by("sort_order", "-created_at")
    )

    if not instruction and not training_docs:
        logger.warning("No agent config or training docs for website %s", website)
        return None

    # Build message history
    messages = []
    for msg in conversation.messages.order_by("created_at").select_related()[:50]:
        role = "user" if msg.direction == "inbound" else "assistant"
        messages.append({"role": role, "content": msg.content})

    if not messages:
        return None

    system_prompt, doc_titles = build_system_prompt(
        instruction=instruction,
        contact=conversation.contact,
        training_docs=training_docs,
    )

    model_name = "claude-sonnet-4-20250514"
    tone_used = instruction.personality if instruction else "professional"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_name,
            max_tokens=300,
            system=system_prompt,
            messages=messages,
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Estimate cost (Claude Sonnet 4 pricing)
        estimated_cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

        # Track AI token usage
        try:
            from core.ai_tracking import record_usage
            record_usage(
                module="messaging", model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            pass

        audit = {
            "tone": tone_used,
            "training_docs": doc_titles,
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
        }

        return AIReplyResult(content=response.content[0].text, audit=audit)

    except Exception as e:
        logger.exception("AI reply generation failed: %s", e)
        return None
