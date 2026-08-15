"""Tests for the plan-derived monthly AI spend allowance.

The cap is margin protection: a user may consume at most
AI_SPEND_CAP_RATIO (65%) of their plan's monthly price as model cost,
resetting each calendar month. Enforced at the provider choke point so
no call site can leak spend.
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import AITokenUsage
from apps.accounts.tests.factories import UserFactory
from core.ai_tracking import (
    AI_SPEND_CAP_RATIO,
    _estimate_cost,
    effective_ai_cap,
    month_to_date_cost,
)


@pytest.mark.django_db
class TestEffectiveCap:
    def test_individual_plan_derives_65_pct(self):
        user = UserFactory(plan="individual")
        assert effective_ai_cap(user) == pytest.approx(45 * AI_SPEND_CAP_RATIO)

    def test_pro_plan_derives_65_pct(self):
        user = UserFactory(plan="pro")
        assert effective_ai_cap(user) == pytest.approx(100 * AI_SPEND_CAP_RATIO)

    def test_manual_cap_only_tightens(self):
        user = UserFactory(plan="individual", monthly_ai_cost_cap_usd=Decimal("10"))
        assert effective_ai_cap(user) == 10.0
        # A manual cap looser than the plan allowance is clamped to the plan.
        user.monthly_ai_cost_cap_usd = Decimal("500")
        assert effective_ai_cap(user) == pytest.approx(45 * AI_SPEND_CAP_RATIO)

    def test_enterprise_custom_price_has_no_derived_cap(self):
        user = UserFactory(plan="enterprise")
        assert effective_ai_cap(user) == 0.0
        user.monthly_ai_cost_cap_usd = Decimal("200")
        assert effective_ai_cap(user) == 200.0

    def test_none_user_unlimited(self):
        assert effective_ai_cap(None) == 0.0


class TestPricing:
    def test_unknown_model_falls_back_conservatively(self):
        # 1M in + 1M out on an unknown model = default $3 + $15.
        assert _estimate_cost("mystery-model", 1_000_000, 1_000_000) == 18.0

    def test_sonar_includes_per_call_fee(self):
        cost = _estimate_cost("sonar", 1000, 1000)
        token_part = (1000 / 1_000_000) * 1.0 * 2
        assert cost == pytest.approx(token_part + 0.008, abs=1e-6)

    def test_grok_and_gemini_priced(self):
        assert _estimate_cost("grok-4", 1_000_000, 0) == 3.0
        assert _estimate_cost("gemini-2.0-flash", 1_000_000, 0) == pytest.approx(0.10)


@pytest.mark.django_db
class TestChokePoint:
    def _spend(self, user, usd):
        # One synthetic row carrying an explicit cost.
        AITokenUsage.objects.create(
            user=user, module="test", provider="anthropic",
            model_name="claude-haiku-4-5", input_tokens=1, output_tokens=1,
            total_tokens=2, estimated_cost_usd=Decimal(str(usd)),
        )

    def test_query_refused_at_cap(self, monkeypatch):
        from apps.llm_ranking.providers.claude import ClaudeProvider

        user = UserFactory(plan="individual")
        self._spend(user, 45 * AI_SPEND_CAP_RATIO)  # exactly at the wall

        provider = ClaudeProvider()
        monkeypatch.setattr(provider, "api_key", "test-key")
        result = provider.query("hello", user=user)
        assert result.succeeded is False
        assert "monthly_ai_allowance_exceeded" in result.error

    def test_query_allowed_under_cap(self, monkeypatch):
        from apps.llm_ranking.providers.claude import ClaudeProvider

        user = UserFactory(plan="individual")
        self._spend(user, 1.0)

        provider = ClaudeProvider()
        monkeypatch.setattr(provider, "api_key", "test-key")
        # Under the cap the wall passes and the call proceeds to the SDK,
        # which we stub to prove the gate (not the network) decided.
        called = {}

        def fake_call(**kwargs):
            called["yes"] = True
            from apps.llm_ranking.providers.base import ProviderResult
            return ProviderResult(succeeded=True, text="ok")

        monkeypatch.setattr(provider, "_call", fake_call)
        result = provider.query("hello", user=user)
        assert called.get("yes") is True
        assert result.succeeded is True

    def test_unattributed_calls_exempt(self, monkeypatch):
        from apps.llm_ranking.providers.claude import ClaudeProvider

        provider = ClaudeProvider()
        monkeypatch.setattr(provider, "api_key", "test-key")

        def fake_call(**kwargs):
            from apps.llm_ranking.providers.base import ProviderResult
            return ProviderResult(succeeded=True, text="ok")

        monkeypatch.setattr(provider, "_call", fake_call)
        assert provider.query("health check").succeeded is True


@pytest.mark.django_db
class TestMonthlyReset:
    def test_previous_month_spend_does_not_count(self):
        user = UserFactory(plan="individual")
        now = timezone.now()
        prev_month = (now.replace(day=1) - timezone.timedelta(days=1)).replace(day=15)
        row = AITokenUsage.objects.create(
            user=user, module="test", provider="anthropic",
            model_name="claude-haiku-4-5", input_tokens=1, output_tokens=1,
            total_tokens=2, estimated_cost_usd=Decimal("100"),
        )
        # created_at is auto_now_add; move it into last month directly.
        AITokenUsage.objects.filter(id=row.id).update(created_at=prev_month)
        assert month_to_date_cost(user) == 0.0
