"""Service-level tests for claim_verifier."""
from __future__ import annotations

import pytest
from django.test import override_settings

from apps.brand_vault.models import BrandFact, FactStatus
from apps.brand_vault.services.embeddings import embed_text
from apps.claim_verifier.models import (
    Claim,
    ClaimMismatch,
    MismatchSeverity,
    MismatchType,
)
from apps.claim_verifier.services.claim_extractor import persist_extracted_items
from apps.claim_verifier.services.severity import bucket
from apps.claim_verifier.services.verifier import (
    compute_audience_reach,
    verify_claim,
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


class TestSeverityBucket:
    def test_critical(self):
        assert bucket(0.85) == MismatchSeverity.CRITICAL.value

    def test_high(self):
        assert bucket(0.6) == MismatchSeverity.HIGH.value

    def test_medium(self):
        assert bucket(0.4) == MismatchSeverity.MEDIUM.value

    def test_low(self):
        assert bucket(0.2) == MismatchSeverity.LOW.value

    def test_info(self):
        assert bucket(0.05) == MismatchSeverity.INFO.value


class TestClaimExtractor:
    def test_filters_non_brand_subjects(self):
        website = WebsiteFactory()
        audit = LLMRankingAuditFactory(website=website, business_name="Acme")
        result = LLMRankingResultFactory(audit=audit)
        items = [
            {"text": "Acme is a SaaS tool", "subject": "Acme",
             "predicate": "is", "object": "A SaaS tool", "confidence": 0.9},
            {"text": "OtherCo is a CRM", "subject": "OtherCo",
             "predicate": "is", "object": "A CRM", "confidence": 0.9},
        ]
        out = persist_extracted_items(items, result=result, brand="Acme")
        assert len(out) == 1
        assert out[0].subject == "Acme"

    def test_keeps_competitor_when_listed(self):
        website = WebsiteFactory()
        audit = LLMRankingAuditFactory(website=website, business_name="Acme")
        result = LLMRankingResultFactory(audit=audit)
        items = [
            {"text": "RivalCo offers webhooks", "subject": "RivalCo",
             "predicate": "offers", "object": "webhooks", "confidence": 0.8},
        ]
        out = persist_extracted_items(items, result=result, brand="Acme",
                                      competitors=["RivalCo"])
        assert len(out) == 1


class TestVerifier:
    def _seed(self, *, fact_object="A SaaS analytics tool"):
        website = WebsiteFactory()
        audit = LLMRankingAuditFactory(website=website, business_name="Acme")
        result = LLMRankingResultFactory(audit=audit)
        fact = BrandFact.objects.create(
            website=website,
            subject="Acme", predicate="is", object=fact_object,
            status=FactStatus.APPROVED, confidence=0.95,
            embedding=embed_text("Acme is " + fact_object),
        )
        return website, audit, result, fact

    def test_match_returns_no_mismatch(self):
        _, _, result, _ = self._seed()
        claim = Claim.objects.create(
            result=result, audit=result.audit, website=result.audit.website,
            text="Acme is a SaaS analytics tool",
            subject="Acme", predicate="is", object="A SaaS analytics tool",
            embedding=embed_text("Acme is A SaaS analytics tool"),
        )
        assert verify_claim(str(claim.id)) is None
        assert not ClaimMismatch.objects.filter(claim=claim).exists()

    def test_contradicts_when_object_differs(self):
        _, _, result, _ = self._seed(fact_object="A SaaS analytics tool")
        claim = Claim.objects.create(
            result=result, audit=result.audit, website=result.audit.website,
            text="Acme is a hardware appliance",
            subject="Acme", predicate="is", object="hardware appliance bare metal server",
            embedding=embed_text("Acme is a hardware appliance bare metal server"),
        )
        mm = verify_claim(str(claim.id))
        assert mm is not None
        assert mm.mismatch_type == MismatchType.CONTRADICTS.value


class TestAudienceReach:
    def _claim(self, *, provider="claude", subject="Acme", prompt="What is Acme?"):
        website = WebsiteFactory()
        audit = LLMRankingAuditFactory(website=website, business_name="Acme")
        result = LLMRankingResultFactory(
            audit=audit, provider=provider, prompt=prompt,
        )
        return Claim.objects.create(
            result=result, audit=audit, website=website,
            text=f"{subject} is", subject=subject,
            predicate="is", object="something",
        )

    def test_provider_weight_scales(self):
        claude_claim = self._claim(provider="claude")
        perplexity_claim = self._claim(provider="perplexity")
        assert compute_audience_reach(claude_claim) > compute_audience_reach(perplexity_claim)

    def test_brand_mention_bonus(self):
        on_brand = self._claim(subject="Acme")
        off_brand = self._claim(subject="OtherCo")
        assert compute_audience_reach(on_brand) > compute_audience_reach(off_brand)

    def test_audience_reach_increases_with_prompt_frequency(self):
        from apps.llm_ranking.tests.factories import LLMRankingResultFactory as RF
        rare = self._claim(prompt="A very rare prompt that is unique")
        common = self._claim(prompt="A repeated common prompt for tests")
        # Seed multiple rows with the same prompt as the common claim
        for _ in range(15):
            RF(audit=common.audit, prompt="A repeated common prompt for tests")
        assert compute_audience_reach(common) > compute_audience_reach(rare)


class TestUnknownWhenNoMatchOriginal:
    """Kept for backward compatibility."""

    def test_unknown_no_match(self):
        website = WebsiteFactory()
        audit = LLMRankingAuditFactory(website=website, business_name="Acme")
        result = LLMRankingResultFactory(audit=audit)
        claim = Claim.objects.create(
            result=result, audit=audit, website=website,
            text="Acme runs on Mars",
            subject="Acme", predicate="runs on", object="Mars",
            embedding=embed_text("Acme runs on Mars"),
        )
        mm = verify_claim(str(claim.id))
        assert mm is not None
        assert mm.mismatch_type == MismatchType.UNKNOWN.value
