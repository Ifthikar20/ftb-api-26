import logging

from django.conf import settings

from apps.strategy.models import ChatMessage
from core.exceptions import AIGenerationFailed

logger = logging.getLogger("apps")


class ChatService:
    @staticmethod
    def send_message(*, website, user, content: str) -> ChatMessage:
        """Process a user message and return an AI response."""
        # Save user message
        ChatMessage.objects.create(
            website=website, user=user, role="user", content=content
        )

        # Build context from recent history
        history = list(
            ChatMessage.objects.filter(website=website)
            .order_by("-created_at")[:20]
            .values("role", "content")
        )
        history.reverse()

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=f"You are an AI growth strategist for {website.name} ({website.url}). "
                       "Provide concise, actionable growth advice. Be specific and data-driven.",
                messages=messages,
            )

            reply = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

        except Exception as e:
            logger.error(f"Chat AI call failed: {e}")
            raise AIGenerationFailed() from e

        ai_message = ChatMessage.objects.create(
            website=website, user=user, role="assistant", content=reply, tokens_used=tokens_used
        )
        return ai_message

    @staticmethod
    def get_history(*, website, limit: int = 50) -> list:
        return list(
            ChatMessage.objects.filter(website=website)
            .order_by("created_at")
            .values("id", "role", "content", "created_at")[:limit]
        )

    @staticmethod
    def clear_history(*, website, user) -> None:
        ChatMessage.objects.filter(website=website).delete()
