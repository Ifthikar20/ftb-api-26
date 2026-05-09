"""API tests for the brand_vault endpoints."""
from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.brand_vault.models import BrandFact, FactStatus
from apps.websites.tests.factories import WebsiteFactory


pytestmark = [
    pytest.mark.django_db,
    override_settings(
        BRAND_VAULT_EXTRACTION_ENABLED=False,
        CLAIM_VERIFICATION_ENABLED=False,
        CITATION_EXTRACTION_ENABLED=False,
    ),
]


@pytest.fixture
def auth_client():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _seed_fact(user, **kwargs):
    website = WebsiteFactory(user=user)
    fact = BrandFact.objects.create(
        website=website, subject="Acme", predicate="is",
        object="A SaaS", status=FactStatus.PENDING, confidence=0.7,
        **kwargs,
    )
    return website, fact


class TestAuth:
    def test_facts_requires_auth(self):
        website = WebsiteFactory()
        url = reverse("brand-vault-website-facts", args=[website.id])
        resp = APIClient().get(url)
        assert resp.status_code == 401


class TestFactsList:
    def test_lists_facts_for_owner(self, auth_client):
        client, user = auth_client
        website, _ = _seed_fact(user)
        url = reverse("brand-vault-website-facts", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 1

    def test_filter_by_status(self, auth_client):
        client, user = auth_client
        website, fact = _seed_fact(user)
        BrandFact.objects.create(
            website=website, subject="Acme", predicate="has", object="API",
            status=FactStatus.APPROVED, confidence=0.95,
        )
        url = reverse("brand-vault-website-facts", args=[website.id])
        resp = client.get(url, {"status": "approved"})
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 1
        assert results[0]["status"] == "approved"

    def test_search_q(self, auth_client):
        client, user = auth_client
        website, _ = _seed_fact(user)
        BrandFact.objects.create(
            website=website, subject="Other", predicate="x", object="y",
            status=FactStatus.PENDING,
        )
        url = reverse("brand-vault-website-facts", args=[website.id])
        resp = client.get(url, {"q": "acme"})
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 1

    def test_tenant_isolation(self, auth_client):
        client, _ = auth_client
        other = UserFactory()
        website, _ = _seed_fact(other)
        url = reverse("brand-vault-website-facts", args=[website.id])
        resp = client.get(url)
        assert resp.status_code in (403, 404)


class TestFactActions:
    def test_approve(self, auth_client):
        client, user = auth_client
        _, fact = _seed_fact(user)
        url = reverse("brand-vault-fact-approve", args=[fact.id])
        resp = client.post(url)
        assert resp.status_code == 200
        fact.refresh_from_db()
        assert fact.status == FactStatus.APPROVED

    def test_reject(self, auth_client):
        client, user = auth_client
        _, fact = _seed_fact(user)
        url = reverse("brand-vault-fact-reject", args=[fact.id])
        resp = client.post(url)
        assert resp.status_code == 200
        fact.refresh_from_db()
        assert fact.status == FactStatus.REJECTED

    def test_edit_supersedes(self, auth_client):
        client, user = auth_client
        _, fact = _seed_fact(user)
        url = reverse("brand-vault-fact-edit", args=[fact.id])
        resp = client.post(url, {
            "subject": "Acme", "predicate": "is", "object": "A new SaaS",
        }, format="json")
        assert resp.status_code == 201
        fact.refresh_from_db()
        assert fact.version_to is not None

    def test_stats(self, auth_client):
        client, user = auth_client
        website, _ = _seed_fact(user)
        url = reverse("brand-vault-website-stats", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.data["total"] >= 1
        assert "by_status" in resp.data
