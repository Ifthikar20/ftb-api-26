"""Tests for email campaigns, tracked links, and new connector services."""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from apps.leads.models import EmailCampaign, CampaignRecipient, LeadSegment
from apps.leads.services.campaign_service import CampaignService
from apps.leads.services.lead_service import LeadService

from apps.leads.tests.factories import (
    WebsiteFactory,
    VisitorFactory,
    LeadFactory,
    LeadSegmentFactory,
)
from apps.accounts.tests.factories import UserFactory


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_and_website():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    return user, website


@pytest.fixture
def leads_with_email(user_and_website):
    user, website = user_and_website
    visitors = [VisitorFactory(website=website) for _ in range(3)]
    leads = [
        LeadFactory(visitor=v, website=website, email=f"lead{i}@example.com", score=75)
        for i, v in enumerate(visitors)
    ]
    return user, website, leads


@pytest.fixture
def auth_client(user_and_website):
    user, website = user_and_website
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, website


# ── CampaignService Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCampaignService:
    def test_create_campaign(self, user_and_website):
        user, website = user_and_website
        campaign = CampaignService.create(
            website=website,
            created_by=user,
            subject="Test Subject",
            body="<p>Hello</p>",
        )
        assert campaign.id is not None
        assert campaign.status == EmailCampaign.STATUS_DRAFT
        assert campaign.subject == "Test Subject"

    def test_create_campaign_with_segment(self, user_and_website):
        user, website = user_and_website
        segment = LeadSegmentFactory(website=website)
        campaign = CampaignService.create(
            website=website,
            created_by=user,
            subject="Segmented",
            body="<p>Hi</p>",
            segment=segment,
        )
        assert campaign.segment == segment

    def test_create_campaign_with_canva_url(self, user_and_website):
        user, website = user_and_website
        campaign = CampaignService.create(
            website=website,
            created_by=user,
            subject="With Canva",
            body="<p>Design</p>",
            canva_design_url="https://www.canva.com/design/abc123/edit",
        )
        assert campaign.canva_design_url == "https://www.canva.com/design/abc123/edit"

    def test_get_campaign(self, user_and_website):
        user, website = user_and_website
        campaign = CampaignService.create(
            website=website, created_by=user, subject="X", body="Y"
        )
        fetched = CampaignService.get(website_id=str(website.id), campaign_id=campaign.id)
        assert fetched.id == campaign.id

    def test_list_campaigns(self, user_and_website):
        user, website = user_and_website
        for i in range(3):
            CampaignService.create(website=website, created_by=user, subject=f"C{i}", body="b")
        campaigns = CampaignService.list(website_id=str(website.id))
        assert campaigns.count() == 3

    def test_send_raises_if_no_leads_with_email(self, user_and_website):
        user, website = user_and_website
        # Lead with no email
        visitor = VisitorFactory(website=website)
        LeadFactory(visitor=visitor, website=website, email="")
        campaign = CampaignService.create(
            website=website, created_by=user, subject="S", body="B"
        )
        with pytest.raises(ValueError, match="No leads"):
            CampaignService.send(campaign=campaign, sent_by=user)

    def test_send_via_sendgrid_marks_sent(self, leads_with_email):
        user, website, leads = leads_with_email
        campaign = CampaignService.create(
            website=website, created_by=user, subject="Hello", body="<p>Hi</p>"
        )
        with patch("apps.notifications.services.email_service.EmailService.send_email", return_value=True):
            result = CampaignService.send(campaign=campaign, sent_by=user)
        result.refresh_from_db()
        assert result.status == EmailCampaign.STATUS_SENT
        assert result.recipient_count == 3

    def test_send_cannot_resend_sent_campaign(self, leads_with_email):
        user, website, leads = leads_with_email
        campaign = CampaignService.create(
            website=website, created_by=user, subject="Re", body="B"
        )
        campaign.status = EmailCampaign.STATUS_SENT
        campaign.save()
        with pytest.raises(ValueError, match="Cannot send"):
            CampaignService.send(campaign=campaign, sent_by=user)

    def test_get_stats(self, user_and_website):
        user, website = user_and_website
        campaign = CampaignService.create(
            website=website, created_by=user, subject="S", body="B"
        )
        stats = CampaignService.get_stats(campaign=campaign)
        assert "recipient_count" in stats
        assert "open_rate" in stats
        assert "click_rate" in stats

    def test_record_open_updates_recipient(self, leads_with_email):
        user, website, leads = leads_with_email
        campaign = CampaignService.create(
            website=website, created_by=user, subject="S", body="B"
        )
        recipient = CampaignRecipient.objects.create(
            campaign=campaign,
            lead=leads[0],
            status=CampaignRecipient.STATUS_SENT,
        )
        CampaignService.record_open(tracking_id=str(recipient.tracking_id))
        recipient.refresh_from_db()
        assert recipient.status == CampaignRecipient.STATUS_OPENED
        assert recipient.opened_at is not None

    def test_record_click_updates_recipient(self, leads_with_email):
        user, website, leads = leads_with_email
        campaign = CampaignService.create(
            website=website, created_by=user, subject="S", body="B"
        )
        recipient = CampaignRecipient.objects.create(
            campaign=campaign,
            lead=leads[0],
            status=CampaignRecipient.STATUS_SENT,
        )
        CampaignService.record_click(tracking_id=str(recipient.tracking_id))
        recipient.refresh_from_db()
        assert recipient.status == CampaignRecipient.STATUS_CLICKED
        assert recipient.clicked_at is not None


# ── Campaign API Views ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCampaignAPI:
    def test_create_campaign_api(self, auth_client):
        client, user, website = auth_client
        response = client.post(
            f"/api/v1/leads/{website.id}/campaigns/",
            {"subject": "API Subject", "body": "<p>Hello</p>"},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["subject"] == "API Subject"
        assert data["status"] == "draft"

    def test_list_campaigns_api(self, auth_client):
        client, user, website = auth_client
        CampaignService.create(website=website, created_by=user, subject="A", body="b")
        CampaignService.create(website=website, created_by=user, subject="B", body="c")
        response = client.get(f"/api/v1/leads/{website.id}/campaigns/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_delete_draft_campaign(self, auth_client):
        client, user, website = auth_client
        campaign = CampaignService.create(website=website, created_by=user, subject="D", body="x")
        response = client.delete(f"/api/v1/leads/{website.id}/campaigns/{campaign.id}/")
        assert response.status_code == 204
        assert not EmailCampaign.objects.filter(id=campaign.id).exists()

    def test_cannot_delete_sending_campaign(self, auth_client):
        client, user, website = auth_client
        campaign = CampaignService.create(website=website, created_by=user, subject="S", body="x")
        campaign.status = EmailCampaign.STATUS_SENDING
        campaign.save()
        response = client.delete(f"/api/v1/leads/{website.id}/campaigns/{campaign.id}/")
        assert response.status_code == 400

    def test_send_campaign_api(self, auth_client):
        client, user, website = auth_client
        visitor = VisitorFactory(website=website)
        LeadFactory(visitor=visitor, website=website, email="target@example.com", score=80)
        campaign = CampaignService.create(website=website, created_by=user, subject="S", body="B")
        with patch("apps.notifications.services.email_service.EmailService.send_email", return_value=True):
            response = client.post(f"/api/v1/leads/{website.id}/campaigns/{campaign.id}/send/")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "sent"

    def test_campaign_stats_api(self, auth_client):
        client, user, website = auth_client
        campaign = CampaignService.create(website=website, created_by=user, subject="S", body="B")
        response = client.get(f"/api/v1/leads/{website.id}/campaigns/{campaign.id}/stats/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "recipient_count" in data
        assert "open_rate" in data


# ── TrackedLink Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTrackedLinks:
    def test_create_tracked_link(self, auth_client):
        client, user, website = auth_client
        response = client.post(
            f"/api/v1/leads/{website.id}/tracked-links/",
            {"destination_url": "https://example.com/landing", "description": "Main CTA"},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert "tracking_key" in data
        assert data["destination_url"] == "https://example.com/landing"
        assert "/t/" in data["short_url"]

    def test_list_tracked_links(self, auth_client):
        client, user, website = auth_client
        from apps.analytics.services.tracking_service import TrackingService
        TrackingService.create_link(website=website, destination_url="https://a.com/")
        TrackingService.create_link(website=website, destination_url="https://b.com/")
        response = client.get(f"/api/v1/leads/{website.id}/tracked-links/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2

    def test_tracked_link_redirect(self, auth_client):
        client, user, website = auth_client
        from apps.analytics.services.tracking_service import TrackingService
        link = TrackingService.create_link(website=website, destination_url="https://example.com/")

        # The redirect view is unauthenticated — use plain client
        anon_client = APIClient()
        response = anon_client.get(f"/t/{link.tracking_key}/")
        assert response.status_code == 302
        assert response["Location"] == "https://example.com/"

    def test_redirect_increments_click_count(self, auth_client):
        client, user, website = auth_client
        from apps.analytics.services.tracking_service import TrackingService
        from apps.analytics.models import TrackedLink
        link = TrackingService.create_link(website=website, destination_url="https://example.com/")

        anon_client = APIClient()
        anon_client.get(f"/t/{link.tracking_key}/")
        link.refresh_from_db()
        assert link.click_count == 1

    def test_redirect_unknown_key_returns_404(self):
        anon_client = APIClient()
        response = anon_client.get("/t/nonexistent123/")
        assert response.status_code == 404

    def test_delete_tracked_link(self, auth_client):
        client, user, website = auth_client
        from apps.analytics.services.tracking_service import TrackingService
        from apps.analytics.models import TrackedLink
        link = TrackingService.create_link(website=website, destination_url="https://x.com/")
        response = client.delete(f"/api/v1/leads/{website.id}/tracked-links/{link.id}/")
        assert response.status_code == 204
        assert not TrackedLink.objects.filter(id=link.id).exists()


# ── Excel Export Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestExcelExport:
    def test_export_xlsx_returns_bytes(self, user_and_website):
        user, website = user_and_website
        visitor = VisitorFactory(website=website)
        LeadFactory(visitor=visitor, website=website, email="x@example.com")
        try:
            xlsx = LeadService.export_xlsx(website_id=str(website.id))
            assert isinstance(xlsx, bytes)
            # Excel files start with PK (ZIP format)
            assert xlsx[:2] == b"PK"
        except RuntimeError as e:
            if "openpyxl" in str(e):
                pytest.skip("openpyxl not installed")
            raise

    def test_export_xlsx_api(self, auth_client):
        client, user, website = auth_client
        visitor = VisitorFactory(website=website)
        LeadFactory(visitor=visitor, website=website, email="y@example.com")
        with patch("apps.leads.services.lead_service.LeadService.export_xlsx", return_value=b"PK\x00\x00"):
            response = client.post(f"/api/v1/leads/{website.id}/export-xlsx/")
        assert response.status_code == 200
        assert "spreadsheetml" in response["Content-Type"]


# ── Hot Lead Notification Tests ───────────────────────────────────────────────

@pytest.mark.django_db
class TestHotLeadNotifications:
    def test_rescore_fires_notification_when_crossing_threshold(self, user_and_website):
        from apps.leads.services.scoring_service import ScoringService
        from apps.notifications.models import Notification

        user, website = user_and_website
        visitor = VisitorFactory(website=website, lead_score=0)

        # Add enough events to cross score threshold of 70
        from apps.leads.tests.factories import PageEventFactory
        for _ in range(5):
            PageEventFactory(visitor=visitor, event_type="form_submit", url="https://x.com/contact")
        for _ in range(3):
            PageEventFactory(visitor=visitor, event_type="pageview", url="https://x.com/pricing")

        with patch("apps.notifications.services.email_service.EmailService.send_email", return_value=True):
            with patch("apps.notifications.services.slack_service.SlackService.send_message", return_value=True):
                ScoringService.rescore_website(website_id=str(website.id))

        # Should have created an in-app notification
        assert Notification.objects.filter(user=user, type="hot_lead").exists()

    def test_rescore_no_double_notification_if_already_hot(self, user_and_website):
        from apps.leads.services.scoring_service import ScoringService
        from apps.notifications.models import Notification

        user, website = user_and_website
        # Visitor already has high score — no threshold crossing
        visitor = VisitorFactory(website=website, lead_score=80)
        from apps.leads.tests.factories import PageEventFactory, LeadFactory
        LeadFactory(visitor=visitor, website=website, score=80)
        PageEventFactory(visitor=visitor, event_type="pageview", url="https://x.com/pricing")

        with patch("apps.notifications.services.email_service.EmailService.send_email", return_value=True):
            ScoringService.rescore_website(website_id=str(website.id))

        # No notification because old_score (80) >= threshold (70) already
        assert not Notification.objects.filter(user=user, type="hot_lead").exists()


# ── Webhook Dispatch Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhookDispatch:
    def test_webhook_dispatch_queues_task(self, user_and_website):
        from apps.websites.models import WebhookEndpoint
        from apps.websites.services.webhook_service import WebhookService

        user, website = user_and_website
        endpoint = WebhookEndpoint.objects.create(
            website=website,
            url="https://hooks.example.com/fetchbot",
            events=["lead.status_changed"],
        )

        with patch("apps.websites.tasks.deliver_webhook.delay") as mock_delay:
            WebhookService.dispatch(
                website=website,
                event="lead.status_changed",
                payload={"lead_id": "abc", "status": "contacted"},
            )
            mock_delay.assert_called_once_with(
                endpoint_id=endpoint.id,
                event="lead.status_changed",
                payload={"lead_id": "abc", "status": "contacted"},
            )

    def test_webhook_dispatch_skips_unsubscribed_events(self, user_and_website):
        from apps.websites.models import WebhookEndpoint
        from apps.websites.services.webhook_service import WebhookService

        user, website = user_and_website
        WebhookEndpoint.objects.create(
            website=website,
            url="https://hooks.example.com/x",
            events=["lead.created"],  # NOT subscribed to lead.status_changed
        )

        with patch("apps.websites.tasks.deliver_webhook.delay") as mock_delay:
            WebhookService.dispatch(
                website=website,
                event="lead.status_changed",
                payload={},
            )
            mock_delay.assert_not_called()

    def test_update_status_dispatches_webhook(self, user_and_website):
        from apps.leads.services.lead_service import LeadService
        from apps.websites.services.webhook_service import WebhookService
        from core.utils.constants import LeadStatus

        user, website = user_and_website
        visitor = VisitorFactory(website=website)
        lead = LeadFactory(visitor=visitor, website=website, status=LeadStatus.NEW)

        with patch("apps.websites.services.webhook_service.WebhookService.dispatch") as mock_dispatch:
            LeadService.update_status(lead=lead, status=LeadStatus.CONTACTED, user=user)
            mock_dispatch.assert_called_once()
            call_kwargs = mock_dispatch.call_args.kwargs
            assert call_kwargs["event"] == "lead.status_changed"
            assert call_kwargs["payload"]["status"] == "contacted"

    def test_webhook_sign_payload(self):
        from apps.websites.services.webhook_service import WebhookService
        sig = WebhookService.sign_payload(secret="mysecret", body='{"test": 1}')
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA256 hex

    def test_webhook_endpoint_subscribes_to_event(self, user_and_website):
        from apps.websites.models import WebhookEndpoint

        _, website = user_and_website
        ep = WebhookEndpoint.objects.create(
            website=website,
            url="https://example.com/",
            events=["lead.scored", "audit.completed"],
        )
        assert ep.subscribes_to("lead.scored")
        assert ep.subscribes_to("audit.completed")
        assert not ep.subscribes_to("lead.created")

    def test_empty_events_list_subscribes_to_all(self, user_and_website):
        from apps.websites.models import WebhookEndpoint

        _, website = user_and_website
        ep = WebhookEndpoint.objects.create(
            website=website,
            url="https://example.com/",
            events=[],  # empty = subscribe to all
        )
        assert ep.subscribes_to("lead.scored")
        assert ep.subscribes_to("anything")


# ── Google Search Status Tests ────────────────────────────────────────────────

@pytest.mark.django_db
class TestAILeadFinderStatus:
    def test_status_endpoint_returns_config_info(self, auth_client):
        client, user, website = auth_client
        response = client.get(f"/api/v1/leads/{website.id}/ai-search/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "google_search_configured" in data
        assert "ai_model_configured" in data

    def test_google_search_not_configured_by_default(self, auth_client):
        client, user, website = auth_client
        with patch("django.conf.settings.GOOGLE_SEARCH_API_KEY", ""):
            with patch("django.conf.settings.GOOGLE_SEARCH_ENGINE_ID", ""):
                response = client.get(f"/api/v1/leads/{website.id}/ai-search/")
        assert response.status_code == 200
