import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.notifications.tasks.send_weekly_reports")
def send_weekly_reports():
    """Send weekly summary reports to all users."""
    from apps.accounts.models import User
    from apps.notifications.services.email_service import EmailService

    for user in User.objects.filter(is_active=True):
        try:
            EmailService.send_email(
                to=user.email,
                subject="Your FetchBot Weekly Report",
                html_content=f"<p>Hi {user.first_name}, here is your weekly growth summary.</p>",
            )
        except Exception as e:
            logger.error(f"Weekly report failed for {user.email}: {e}")


@shared_task(name="apps.notifications.tasks.send_daily_growth_reports")
def send_daily_growth_reports():
    """
    Send daily growth reports to all active IntegrationConnections.
    Queries analytics, leads, and keyword data, then formats per platform.
    Runs daily via Celery beat.
    """
    from apps.notifications.models import IntegrationConnection

    connections = IntegrationConnection.objects.filter(
        is_active=True, notify_daily_report=True
    ).select_related("user")

    if not connections.exists():
        logger.info("No active integration connections for daily reports")
        return

    today = date.today().strftime("%A, %b %d")

    for conn in connections:
        try:
            # Gather data for this user's websites
            report = _build_report_data(conn.user)

            if conn.platform == "slack":
                _send_slack_report(conn.webhook_url, report, today)
            elif conn.platform == "discord":
                _send_discord_report(conn.webhook_url, report, today)
            elif conn.platform == "telegram":
                _send_telegram_report(conn.webhook_url, report, today)

            logger.info(f"Daily report sent to {conn.platform} for {conn.user.email}")

        except Exception as e:
            logger.error(f"Daily report failed for {conn.user.email} ({conn.platform}): {e}")


def _build_report_data(user) -> dict:
    """Gather analytics data for a user's websites."""
    from apps.websites.models import Website

    websites = Website.objects.filter(organization__users=user)
    data = {
        "visitors_24h": 0,
        "pageviews_24h": 0,
        "visitors_change": 0,
        "top_page": None,
    }

    for website in websites[:3]:  # Limit to first 3 websites
        try:
            # Analytics overview
            from apps.analytics.services.analytics_service import AnalyticsService
            overview = AnalyticsService.get_overview(
                website_id=str(website.id), period="24h"
            )
            if isinstance(overview, dict):
                data["visitors_24h"] += overview.get("unique_visitors", 0)
                data["pageviews_24h"] += overview.get("total_pageviews", 0)
                data["visitors_change"] = overview.get("visitor_change_pct", 0)
                # Top page
                top_pages = overview.get("top_pages", [])
                if top_pages and not data["top_page"]:
                    data["top_page"] = top_pages[0].get("path", "/")
        except Exception:
            pass

    return data


def _send_slack_report(webhook_url: str, data: dict, today: str):
    """Format and send a Slack block kit message."""
    from apps.notifications.services.slack_service import SlackService

    change = data["visitors_change"]
    change_str = f"+{change}%" if change >= 0 else f"{change}%"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Daily Growth Report — {today}", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{data['visitors_24h']:,}* visitors\n_{change_str} from yesterday_"},
                {"type": "mrkdwn", "text": f"*{data['pageviews_24h']:,}* pageviews"},
            ],
        },
    ]

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "📎 <https://app.fetchbot.ai|View full dashboard>"}],
    })

    SlackService.send_message(
        webhook_url=webhook_url,
        text=f"📊 Daily Growth Report — {today}",
        blocks=blocks,
    )


def _send_discord_report(webhook_url: str, data: dict, today: str):
    """Format and send a Discord embed message."""
    from apps.notifications.services.discord_service import DiscordService

    change = data["visitors_change"]
    change_str = f"+{change}%" if change >= 0 else f"{change}%"

    fields = [
        {"name": "Visitors", "value": f"**{data['visitors_24h']:,}**\n{change_str} from yesterday", "inline": True},
        {"name": "Pageviews", "value": f"**{data['pageviews_24h']:,}**", "inline": True},
    ]

    DiscordService.send_message(
        webhook_url=webhook_url,
        title=f"📊 Daily Growth Report — {today}",
        fields=fields,
        footer="📎 View full dashboard at app.fetchbot.ai",
    )


def _send_telegram_report(chat_id: str, data: dict, today: str):
    """Format and send a Telegram Markdown message."""
    from apps.notifications.services.telegram_service import TelegramService

    change = data["visitors_change"]
    change_str = f"+{change}%" if change >= 0 else f"{change}%"

    text = (
        f"*Daily Growth Report*\n_{today}_\n\n"
        f"*{data['visitors_24h']:,}* visitors · {change_str} from yesterday\n"
        f"*{data['pageviews_24h']:,}* pageviews\n\n"
        f"_View full dashboard at app.fetchbot.ai_"
    )

    TelegramService.send_message(chat_id=chat_id, text=text)
