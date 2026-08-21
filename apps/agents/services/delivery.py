"""Deliver an agent insight to its channels (in-app + Slack/Discord outbound)."""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")


def _discord_fields(insight) -> list:
    points = (insight.data or {}).get("key_points") or []
    if not points:
        return []
    bullets = "\n".join(f"- {str(p)[:200]}" for p in points[:4])
    return [{"name": "Key points", "value": bullets[:1024], "inline": False}]


def _slack_blocks(insight) -> list:
    spec_name = insight.hired_agent.agent_key.replace("_", " ").title()
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": insight.title[:150]}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"*{spec_name}* · {insight.run_date.isoformat()}"}
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": insight.summary_markdown[:2900] or "_No summary._"}},
    ]
    points = (insight.data or {}).get("key_points") or []
    if points:
        bullets = "\n".join(f"• {str(p)[:200]}" for p in points[:4])
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": bullets}})
    return blocks


def deliver(insight) -> list[str]:
    """Send the insight in-app and (if connected) to Slack. Returns channels used."""
    channels: list[str] = []
    hired = insight.hired_agent

    # In-app notification (durable record + WebSocket push).
    try:
        from apps.notifications.services.notification_service import NotificationService

        NotificationService.create(
            user=hired.user,
            notification_type="agent_insight",
            title=insight.title[:200],
            message=insight.summary_markdown[:500],
            data={
                "hired_agent_id": str(hired.id),
                "insight_id": str(insight.id),
                "website_id": str(hired.website_id),
                "agent_key": hired.agent_key,
            },
            action_url=f"/agents/{hired.agent_key}?website={hired.website_id}",
        )
        channels.append("in_app")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("agent in-app delivery failed: %s", exc)

    # Platform outbound (reuses the existing IntegrationConnection webhook).
    # The FK is named slack_connection for historical reasons but may point
    # at any platform's connection - branch on conn.platform.
    conn = hired.slack_connection
    if conn and conn.is_active and conn.webhook_url:
        if conn.platform == "discord":
            try:
                from apps.notifications.services.discord_service import DiscordService

                ok = DiscordService.send_message(
                    webhook_url=conn.webhook_url,
                    title=insight.title[:150],
                    description=(insight.summary_markdown or "")[:2000] or "No summary.",
                    fields=_discord_fields(insight),
                )
                if ok:
                    channels.append("discord")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("agent discord delivery failed: %s", exc)
        else:
            try:
                from apps.notifications.services.slack_service import SlackService

                ok = SlackService.send_message(
                    webhook_url=conn.webhook_url,
                    text=insight.title[:200],
                    blocks=_slack_blocks(insight),
                )
                if ok:
                    channels.append("slack")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("agent slack delivery failed: %s", exc)

    insight.delivered_channels = channels
    insight.save(update_fields=["delivered_channels", "updated_at"])
    return channels
