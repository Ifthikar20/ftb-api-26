"""
Telegram Bot API Service — Send notifications via Telegram.
Uses the Telegram Bot API (sendMessage endpoint).
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("apps")


class TelegramService:
    @staticmethod
    def _get_bot_token() -> str:
        return getattr(settings, "TELEGRAM_BOT_TOKEN", "")

    @staticmethod
    def send_message(*, chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a Markdown-formatted message to a Telegram chat."""
        bot_token = TelegramService._get_bot_token()
        if not bot_token or not chat_id:
            logger.warning("Telegram not configured (missing bot token or chat_id)")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()
            if data.get("ok"):
                return True
            logger.warning(f"Telegram API error: {data.get('description', 'unknown')}")
            return False
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    @staticmethod
    def send_hot_lead_alert(*, chat_id: str, lead) -> bool:
        """Send a hot lead alert to Telegram."""
        text = (
            f"🔥 *Hot Lead Detected*\n\n"
            f"Score: *{lead.score}*\n"
            f"Company: {lead.company or 'Unknown'}\n"
            f"Website: {lead.website.name}"
        )
        return TelegramService.send_message(chat_id=chat_id, text=text)
