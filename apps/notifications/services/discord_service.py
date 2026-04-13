"""
Discord Webhook Service — Send rich embed messages to Discord channels.
"""
import logging

import requests

logger = logging.getLogger("apps")

# FetchBot brand color
BRAND_COLOR = 0x8b5cf6  # Purple


class DiscordService:
    @staticmethod
    def send_message(*, webhook_url: str, title: str = "", description: str = "",
                     fields: list = None, footer: str = "", color: int = None) -> bool:
        """Send a rich embed message to a Discord webhook."""
        if not webhook_url:
            return False

        embed = {
            "color": color or BRAND_COLOR,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        if title:
            embed["title"] = title
        if description:
            embed["description"] = description
        if fields:
            embed["fields"] = fields
        if footer:
            embed["footer"] = {"text": footer}

        payload = {
            "username": "FetchBot",
            "embeds": [embed],
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    @staticmethod
    def send_hot_lead_alert(*, webhook_url: str, lead) -> bool:
        """Send a hot lead alert to Discord."""
        return DiscordService.send_message(
            webhook_url=webhook_url,
            title="🔥 Hot Lead Detected",
            description=f"Score: **{lead.score}**",
            fields=[
                {"name": "Company", "value": lead.company or "Unknown", "inline": True},
                {"name": "Website", "value": lead.website.name, "inline": True},
            ],
            color=0xef4444,
        )
