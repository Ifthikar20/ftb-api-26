import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.leads.models import LeadSegment, ScoringConfig
from apps.leads.tests.factories import (
    LeadFactory,
    LeadSegmentFactory,
    ScoringConfigFactory,
    VisitorFactory,
    WebsiteFactory,
)
from core.utils.constants import LeadStatus


@pytest.fixture
def auth_client():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def website_with_leads():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    v1 = VisitorFactory(website=website)
    v2 = VisitorFactory(website=website)
    lead1 = LeadFactory(visitor=v1, website=website, score=80)
    lead2 = LeadFactory(visitor=v2, website=website, score=40)
    return user, website, lead1, lead2


@pytest.mark.django_db
class TestLeadListView:
    def test_list_leads_authenticated(self, website_with_leads):
        user, website, lead1, lead2 = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["results"]) == 2

    def test_list_leads_unauthenticated(self, website_with_leads):
        _, website, _, _ = website_with_leads
        client = APIClient()
        response = client.get(f"/api/v1/leads/{website.id}/")
        assert response.status_code == 401

    def test_list_leads_wrong_user(self, website_with_leads):
        _, website, _, _ = website_with_leads
        other_user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=other_user)

        response = client.get(f"/api/v1/leads/{website.id}/")
        assert response.status_code == 404

    def test_list_leads_filter_by_min_score(self, website_with_leads):
        user, website, lead1, lead2 = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/?min_score=70")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 1
        assert results[0]["score"] == 80

    def test_list_leads_filter_by_status(self, website_with_leads):
        user, website, lead1, lead2 = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        lead1.status = LeadStatus.QUALIFIED
        lead1.save()

        response = client.get(f"/api/v1/leads/{website.id}/?status=qualified")
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert len(results) == 1


@pytest.mark.django_db
class TestHotLeadsView:
    def test_hot_leads_returns_paginated_results(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        v1 = VisitorFactory(website=website)
        v2 = VisitorFactory(website=website)
        LeadFactory(visitor=v1, website=website, score=85)
        LeadFactory(visitor=v2, website=website, score=40)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/hot/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == 85

    def test_hot_leads_unauthenticated(self):
        website = WebsiteFactory()
        client = APIClient()
        response = client.get(f"/api/v1/leads/{website.id}/hot/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestLeadDetailView:
    def test_get_lead_detail(self, website_with_leads):
        user, website, lead1, _ = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/{lead1.id}/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(lead1.id)
        assert data["score"] == lead1.score

    def test_get_lead_detail_not_found(self):
        import uuid
        user = UserFactory()
        website = WebsiteFactory(user=user)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/{uuid.uuid4()}/")
        assert response.status_code == 404

    def test_put_lead_updates_status(self, website_with_leads):
        user, website, lead1, _ = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(
            f"/api/v1/leads/{website.id}/{lead1.id}/",
            {"status": "contacted"},
            format="json",
        )
        assert response.status_code == 200
        lead1.refresh_from_db()
        assert lead1.status == LeadStatus.CONTACTED

    def test_put_lead_no_status_returns_unchanged(self, website_with_leads):
        user, website, lead1, _ = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(
            f"/api/v1/leads/{website.id}/{lead1.id}/",
            {},
            format="json",
        )
        assert response.status_code == 200
        lead1.refresh_from_db()
        assert lead1.status == LeadStatus.NEW


@pytest.mark.django_db
class TestLeadNoteView:
    def test_create_note(self, website_with_leads):
        user, website, lead1, _ = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f"/api/v1/leads/{website.id}/{lead1.id}/note/",
            {"content": "Called this lead today."},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["content"] == "Called this lead today."

    def test_create_note_unauthenticated(self, website_with_leads):
        _, website, lead1, _ = website_with_leads
        client = APIClient()
        response = client.post(
            f"/api/v1/leads/{website.id}/{lead1.id}/note/",
            {"content": "Unauthorized note"},
            format="json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestLeadExportView:
    def test_export_csv(self, website_with_leads):
        user, website, lead1, lead2 = website_with_leads
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f"/api/v1/leads/{website.id}/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "attachment" in response["Content-Disposition"]
        content = response.content.decode("utf-8")
        assert "ID,Score,Status" in content

    def test_export_csv_unauthenticated(self, website_with_leads):
        _, website, _, _ = website_with_leads
        client = APIClient()
        response = client.post(f"/api/v1/leads/{website.id}/export/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestLeadSegmentListView:
    def test_list_segments(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        LeadSegmentFactory(website=website, name="High Value")
        LeadSegmentFactory(website=website, name="Tech Companies")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/segments/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2

    def test_create_segment(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            f"/api/v1/leads/{website.id}/segments/",
            {"name": "Hot Leads", "rules": {"min_score": 70}},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "Hot Leads"
        assert LeadSegment.objects.filter(website=website).count() == 1

    def test_list_segments_unauthenticated(self):
        website = WebsiteFactory()
        client = APIClient()
        response = client.get(f"/api/v1/leads/{website.id}/segments/")
        assert response.status_code == 401

    def test_list_segments_wrong_user(self):
        owner = UserFactory()
        other = UserFactory()
        website = WebsiteFactory(user=owner)
        LeadSegmentFactory(website=website)

        client = APIClient()
        client.force_authenticate(user=other)
        response = client.get(f"/api/v1/leads/{website.id}/segments/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestLeadSegmentDetailView:
    def test_update_segment(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        segment = LeadSegmentFactory(website=website, name="Old Name")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(
            f"/api/v1/leads/{website.id}/segments/{segment.id}/",
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == 200
        segment.refresh_from_db()
        assert segment.name == "New Name"

    def test_delete_segment(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        segment = LeadSegmentFactory(website=website)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(f"/api/v1/leads/{website.id}/segments/{segment.id}/")
        assert response.status_code == 204
        assert not LeadSegment.objects.filter(id=segment.id).exists()

    def test_delete_segment_not_found(self):
        import uuid
        user = UserFactory()
        website = WebsiteFactory(user=user)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(f"/api/v1/leads/{website.id}/segments/{uuid.uuid4()}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestScoringConfigView:
    def test_get_scoring_config_creates_default(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/scoring-config/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["threshold"] == 70
        assert ScoringConfig.objects.filter(website=website).count() == 1

    def test_get_scoring_config_returns_existing(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        ScoringConfigFactory(website=website, threshold=50)

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/leads/{website.id}/scoring-config/")
        assert response.status_code == 200
        assert response.json()["data"]["threshold"] == 50

    def test_put_scoring_config_updates_threshold(self):
        user = UserFactory()
        website = WebsiteFactory(user=user)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(
            f"/api/v1/leads/{website.id}/scoring-config/",
            {"threshold": 80, "weights": {"form_submit": 50}},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["threshold"] == 80
        assert data["weights"]["form_submit"] == 50

    def test_scoring_config_unauthenticated(self):
        website = WebsiteFactory()
        client = APIClient()
        response = client.get(f"/api/v1/leads/{website.id}/scoring-config/")
        assert response.status_code == 401
