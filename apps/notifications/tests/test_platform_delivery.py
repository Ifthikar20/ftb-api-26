"""Tests for platform-aware outbound delivery (agent insights + hot leads)."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.agents.models import AgentInsight, HiredAgent
from apps.agents.services.delivery import deliver
from apps.notifications.models import IntegrationConnection
from apps.websites.tests.factories import WebsiteFactory

SLACK_URL = "https://hooks.slack.com/services/T0/B0/xyz"
DISCORD_URL = "https://discord.com/api/webhooks/123/token-abc"


def _insight(user, website, connection) -> AgentInsight:
    hired = HiredAgent.objects.create(
        user=user, website=website, created_by=user,
        agent_key="visibility_analyst", slack_connection=connection,
    )
    return AgentInsight.objects.create(
        hired_agent=hired, run_date=date.today(),
        title="Visibility moved", summary_markdown="Up 4 points.",
        data={"key_points": ["Claude mentions doubled", "New citation source"]},
    )


@pytest.mark.django_db
class TestInsightDelivery:
    def test_discord_connection_routes_to_discord_service(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        connection = IntegrationConnection.objects.create(
            user=user, platform="discord", webhook_url=DISCORD_URL,
        )
        insight = _insight(user, website, connection)

        response = MagicMock(status_code=204)
        with patch("apps.notifications.services.notification_service.channel_layer"), \
             patch(
                 "apps.notifications.services.discord_service.requests.post",
                 return_value=response,
             ) as mock_post:
            channels = deliver(insight)

        assert "discord" in channels
        assert "in_app" in channels
        assert mock_post.call_args.args[0] == DISCORD_URL
        embeds = mock_post.call_args.kwargs["json"]["embeds"]
        assert embeds[0]["title"] == "Visibility moved"
        insight.refresh_from_db()
        assert "discord" in insight.delivered_channels

    def test_slack_connection_still_uses_slack_service(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        connection = IntegrationConnection.objects.create(
            user=user, platform="slack", webhook_url=SLACK_URL,
        )
        insight = _insight(user, website, connection)

        response = MagicMock(status_code=200)
        with patch("apps.notifications.services.notification_service.channel_layer"), \
             patch(
                 "apps.notifications.services.slack_service.requests.post",
                 return_value=response,
             ) as mock_post:
            channels = deliver(insight)

        assert "slack" in channels
        assert mock_post.call_args.args[0] == SLACK_URL


@pytest.mark.django_db
class TestHotLeadDispatch:
    def test_slack_integration_connection_receives_hot_lead(self):
        """A user with only an IntegrationConnection (no legacy prefs webhook)
        must still get the Slack hot-lead alert."""
        from apps.notifications.services.notification_service import NotificationService

        user = UserFactory()
        website = WebsiteFactory(user=user)
        IntegrationConnection.objects.create(
            user=user, platform="slack", webhook_url=SLACK_URL,
        )
        lead = MagicMock()
        lead.id = "00000000-0000-0000-0000-000000000001"
        lead.score = 91
        lead.company = "Acme"
        lead.website = website
        lead.website_id = website.id

        response = MagicMock(status_code=200)
        with patch("apps.notifications.services.notification_service.channel_layer"), \
             patch(
                 "apps.notifications.services.email_service.EmailService.send_hot_lead_alert",
             ), \
             patch(
                 "apps.notifications.services.slack_service.requests.post",
                 return_value=response,
             ) as mock_post:
            NotificationService.fire_hot_lead(user=user, lead=lead)

        assert mock_post.called
        assert mock_post.call_args.args[0] == SLACK_URL

    def test_same_webhook_not_double_sent(self):
        """Legacy prefs path + IntegrationConnection with the same webhook
        must produce exactly one Slack send."""
        from apps.notifications.models import NotificationPreference
        from apps.notifications.services.notification_service import NotificationService

        user = UserFactory()
        website = WebsiteFactory(user=user)
        NotificationPreference.objects.create(
            user=user, hot_lead_slack=True, slack_webhook_url=SLACK_URL,
        )
        IntegrationConnection.objects.create(
            user=user, platform="slack", webhook_url=SLACK_URL,
        )
        lead = MagicMock()
        lead.id = "00000000-0000-0000-0000-000000000002"
        lead.score = 88
        lead.company = "Acme"
        lead.website = website
        lead.website_id = website.id

        response = MagicMock(status_code=200)
        with patch("apps.notifications.services.notification_service.channel_layer"), \
             patch(
                 "apps.notifications.services.email_service.EmailService.send_hot_lead_alert",
             ), \
             patch(
                 "apps.notifications.services.slack_service.requests.post",
                 return_value=response,
             ) as mock_post:
            NotificationService.fire_hot_lead(user=user, lead=lead)

        slack_sends = [
            call for call in mock_post.call_args_list
            if call.args and call.args[0] == SLACK_URL
        ]
        assert len(slack_sends) == 1
