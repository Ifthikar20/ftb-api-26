"""API tests for the claim_verifier endpoints."""
from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.claim_verifier.models import (
    Claim,
    ClaimMismatch,
    MismatchSeverity,
    MismatchType,
)
from apps.llm_ranking.tests.factories import (
    LLMRankingAuditFactory,
    LLMRankingResultFactory,
)
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


def _seed_mismatch(user, *, severity=MismatchSeverity.HIGH):
    website = WebsiteFactory(user=user)
    audit = LLMRankingAuditFactory(website=website, created_by=user)
    result = LLMRankingResultFactory(audit=audit)
    claim = Claim.objects.create(
        result=result, audit=audit, website=website,
        text="Acme is X",
        subject="Acme", predicate="is", object="X",
    )
    mm = ClaimMismatch.objects.create(
        claim=claim,
        mismatch_type=MismatchType.UNKNOWN.value,
        severity=severity.value,
        factual_divergence=0.6,
        audience_reach=1.0,
        explanation="No matching fact.",
    )
    return website, audit, claim, mm


class TestAuth:
    def test_mismatches_requires_auth(self):
        website = WebsiteFactory()
        url = reverse("claim-verifier-website-mismatches", args=[website.id])
        resp = APIClient().get(url)
        assert resp.status_code == 401


class TestWebsiteMismatches:
    def test_lists_for_owner(self, auth_client):
        client, user = auth_client
        website, _, _, _ = _seed_mismatch(user)
        url = reverse("claim-verifier-website-mismatches", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 1

    def test_filter_by_severity(self, auth_client):
        client, user = auth_client
        website, _, _, _ = _seed_mismatch(user, severity=MismatchSeverity.HIGH)
        url = reverse("claim-verifier-website-mismatches", args=[website.id])
        resp = client.get(url, {"severity": "low"})
        results = resp.data["results"] if "results" in resp.data else resp.data
        assert len(results) == 0

    def test_tenant_isolation(self, auth_client):
        client, _ = auth_client
        other = UserFactory()
        website, _, _, _ = _seed_mismatch(other)
        url = reverse("claim-verifier-website-mismatches", args=[website.id])
        resp = client.get(url)
        assert resp.status_code in (403, 404)


class TestAccuracy:
    def test_returns_payload(self, auth_client):
        client, user = auth_client
        website, _, _, _ = _seed_mismatch(user)
        url = reverse("claim-verifier-website-accuracy", args=[website.id])
        resp = client.get(url)
        assert resp.status_code == 200
        body = resp.data
        assert "total_claims" in body
        assert "mismatched" in body
        assert "accuracy_rate" in body
        assert body["mismatched"] == 1


class TestDismiss:
    def test_dismiss_marks_flag(self, auth_client):
        client, user = auth_client
        _, _, _, mm = _seed_mismatch(user)
        url = reverse("claim-verifier-mismatch-dismiss", args=[mm.id])
        resp = client.post(url)
        assert resp.status_code == 200
        mm.refresh_from_db()
        assert mm.dismissed is True


class TestAuditClaims:
    def test_lists_claims(self, auth_client):
        client, user = auth_client
        _, audit, claim, _ = _seed_mismatch(user)
        url = reverse("claim-verifier-audit-claims", args=[audit.id])
        resp = client.get(url)
        assert resp.status_code == 200
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert any(str(c["id"]) == str(claim.id) for c in data)
