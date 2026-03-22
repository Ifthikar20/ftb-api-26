import logging

import requests

logger = logging.getLogger("apps")


class SlackService:
    @staticmethod
    def send_message(*, webhook_url: str, text: str, blocks: list = None) -> bool:
        """Send a message to a Slack webhook."""
        if not webhook_url:
            return False

        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    @staticmethod
    def send_hot_lead_alert(*, user, lead) -> None:
        try:
            prefs = user.notification_preferences
            if not prefs.hot_lead_slack or not prefs.slack_webhook_url:
                return
            SlackService.send_message(
                webhook_url=prefs.slack_webhook_url,
                text=f":fire: Hot lead detected! Score: {lead.score}",
            )
        except Exception:
            pass
