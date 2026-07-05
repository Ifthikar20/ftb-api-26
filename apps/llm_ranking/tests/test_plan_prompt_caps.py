"""
Asserts the per-plan ``max_prompts_per_audit`` cap is enforced both
in ``max_prompts_for_user`` (the lookup) and in
``LLMRankingService.generate_prompts`` (the consumer).
"""
from unittest.mock import MagicMock

import pytest

from core.utils.constants import Plan, max_prompts_for_user


@pytest.fixture(autouse=True)
def _paywall_on(settings):
    # These tests assert plan gating, which only applies while the
    # paywall is enabled (PAYWALL_ENABLED defaults to False).
    settings.PAYWALL_ENABLED = True


class _FakeSub:
    def __init__(self, plan):
        self.plan = plan


class _FakeUser:
    def __init__(self, plan):
        self.subscription = _FakeSub(plan) if plan else None


class TestMaxPromptsForUser:
    def test_individual_returns_5(self):
        assert max_prompts_for_user(_FakeUser(Plan.INDIVIDUAL)) == 5

    def test_pro_returns_15(self):
        assert max_prompts_for_user(_FakeUser(Plan.PRO)) == 15

    def test_enterprise_returns_50(self):
        assert max_prompts_for_user(_FakeUser(Plan.ENTERPRISE)) == 50

    def test_no_subscription_falls_back_to_individual(self):
        user = MagicMock()
        # Simulate the OneToOne reverse relation raising
        # Subscription.DoesNotExist when accessed.
        type(user).subscription = property(
            fget=lambda self: (_ for _ in ()).throw(AttributeError("missing")),
        )
        # The helper should not propagate the error.
        assert max_prompts_for_user(user) == 5

    def test_unknown_plan_falls_back_to_individual(self):
        assert max_prompts_for_user(_FakeUser("ghost-tier")) == 5

    def test_legacy_starter_resolves_to_individual_limit(self):
        # Subscriptions on the old "starter" plan should keep working.
        assert max_prompts_for_user(_FakeUser(Plan.STARTER)) == 5


@pytest.mark.django_db
class TestGeneratePromptsRespectsPlan:
    """generate_prompts must cap its returned list at the user's plan limit."""

    def test_individual_returns_at_most_5(self, settings):
        # Disable the Claude variants path so the test stays hermetic
        # — the deterministic library alone produces > 5 prompts so we
        # can verify the cap is the binding constraint.
        settings.ANTHROPIC_API_KEY = ""

        from apps.llm_ranking.services.ranking_service import LLMRankingService
        prompts = LLMRankingService.generate_prompts(
            business_name="Acme",
            industry="SaaS analytics",
            description="Acme builds growth analytics for SaaS teams.",
            keywords=["analytics", "growth"],
            user=_FakeUser(Plan.INDIVIDUAL),
        )
        assert len(prompts) <= 5
        # Each prompt has the standard shape regardless of cap
        assert all("text" in p and "type" in p for p in prompts)

    def test_pro_returns_more_than_individual(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        from apps.llm_ranking.services.ranking_service import LLMRankingService
        ind = LLMRankingService.generate_prompts(
            business_name="Acme", industry="SaaS analytics",
            description="Growth analytics.",
            keywords=["analytics"],
            user=_FakeUser(Plan.INDIVIDUAL),
        )
        pro = LLMRankingService.generate_prompts(
            business_name="Acme", industry="SaaS analytics",
            description="Growth analytics.",
            keywords=["analytics"],
            user=_FakeUser(Plan.PRO),
        )
        assert len(pro) > len(ind)
        assert len(pro) <= 15

    def test_no_user_defaults_to_individual_cap(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        from apps.llm_ranking.services.ranking_service import LLMRankingService
        prompts = LLMRankingService.generate_prompts(
            business_name="Acme", industry="SaaS analytics",
            description="x", keywords=["analytics"],
        )
        assert len(prompts) <= 5
