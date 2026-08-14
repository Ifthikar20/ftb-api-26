"""
Both audit-creation paths must go through the same entitlement gate.

Regression context: ``WebsitePromptCreateView._trigger_scan`` created an
``LLMRankingAudit`` and dispatched it without any of the checks that
``LLMRankingAuditListView.post`` applied. Creating prompts was therefore an
unmetered way to run audits — no spend cap, every configured provider
regardless of plan, no prompt cap — and the create handler splits input per
line with bulk upload, so one paste could queue hundreds of prompts.

``providers_allowed`` and the per-plan prompt cap on *custom* prompts were
never enforced on either path.
"""
from unittest.mock import patch

import pytest

from apps.llm_ranking.services.entitlements import (
    AuditNotAllowed,
    assert_within_spend_cap,
    cap_prompts,
    resolve_providers,
)
from core.utils.constants import Plan


class _FakeSub:
    def __init__(self, plan):
        self.plan = plan


class _FakeUser:
    """Stand-in for a User with a subscription and a spend cap."""

    def __init__(self, plan=None, cap=0, spent=0.0):
        self.id = "test-user"
        self.subscription = _FakeSub(plan) if plan else None
        self.monthly_ai_cost_cap_usd = cap
        self._spent = spent


@pytest.fixture
def paywall_on(settings):
    """Plan gates short-circuit to Enterprise unless the paywall is enabled."""
    settings.PAYWALL_ENABLED = True


@pytest.fixture
def all_keys(settings):
    """Configure every provider so key availability isn't the filter."""
    settings.ANTHROPIC_API_KEY = "test"
    settings.OPENAI_API_KEY = "test"
    settings.GEMINI_API_KEY = "test"
    settings.GOOGLE_API_KEY = "test"
    settings.PERPLEXITY_API_KEY = "test"
    settings.XAI_API_KEY = "test"


class TestSpendCap:
    def test_no_cap_passes(self):
        assert_within_spend_cap(_FakeUser(cap=0))  # returns None, no raise

    def test_under_cap_passes(self):
        with patch("core.ai_tracking.month_to_date_cost", return_value=4.0):
            assert_within_spend_cap(_FakeUser(cap=10.0))

    def test_at_cap_raises(self):
        with patch("core.ai_tracking.month_to_date_cost", return_value=10.0):
            with pytest.raises(AuditNotAllowed) as exc:
                assert_within_spend_cap(_FakeUser(cap=10.0))
        assert exc.value.code == "monthly_ai_cost_cap_exceeded"
        assert exc.value.http_status == 402
        assert exc.value.payload["cap_status"]["cap_usd"] == 10.0


class TestResolveProviders:
    def test_plan_restricts_providers(self, paywall_on, all_keys):
        """An Individual plan allows claude+gpt4 only, even with all keys set.

        This is the leak: the pricing table advertises the restriction and
        nothing enforced it, so every user got every configured provider —
        doubling per-prompt cost on the cheapest tier.
        """
        resolved = resolve_providers(_FakeUser(Plan.INDIVIDUAL), None)
        assert set(resolved) <= {"claude", "gpt4"}
        assert "gemini" not in resolved
        assert "grok" not in resolved

    def test_pro_plan_gets_more(self, paywall_on, all_keys):
        pro = set(resolve_providers(_FakeUser(Plan.PRO), None))
        individual = set(resolve_providers(_FakeUser(Plan.INDIVIDUAL), None))
        assert individual < pro

    def test_explicit_request_still_plan_capped(self, paywall_on, all_keys):
        """Asking for a disallowed provider does not grant it."""
        resolved = resolve_providers(
            _FakeUser(Plan.INDIVIDUAL), ["claude", "gemini", "perplexity"],
        )
        assert "gemini" not in resolved
        assert "perplexity" not in resolved

    def test_unconfigured_provider_dropped(self, paywall_on, settings):
        settings.ANTHROPIC_API_KEY = "test"
        settings.OPENAI_API_KEY = ""
        assert "gpt4" not in resolve_providers(_FakeUser(Plan.PRO), ["claude", "gpt4"])

    def test_unknown_provider_dropped(self, paywall_on, all_keys):
        assert "nope" not in resolve_providers(_FakeUser(Plan.PRO), ["claude", "nope"])

    def test_never_returns_empty(self, paywall_on, settings):
        """An audit with no providers produces nothing — always fall back."""
        settings.ANTHROPIC_API_KEY = ""
        settings.OPENAI_API_KEY = ""
        assert resolve_providers(_FakeUser(Plan.INDIVIDUAL), []) != []

    def test_paywall_off_allows_everything(self, settings, all_keys):
        """PAYWALL_ENABLED is false by default, so gates are inert until enabled."""
        settings.PAYWALL_ENABLED = False
        resolved = resolve_providers(_FakeUser(Plan.INDIVIDUAL), None)
        assert "gemini" in resolved


class TestCapPrompts:
    def test_truncates_to_plan_cap(self, paywall_on):
        prompts = [{"text": f"q{i}"} for i in range(20)]
        assert len(cap_prompts(_FakeUser(Plan.INDIVIDUAL), prompts)) == 5

    def test_pro_gets_more(self, paywall_on):
        prompts = [{"text": f"q{i}"} for i in range(20)]
        assert len(cap_prompts(_FakeUser(Plan.PRO), prompts)) == 15

    def test_under_cap_untouched(self, paywall_on):
        prompts = [{"text": "q1"}, {"text": "q2"}]
        assert cap_prompts(_FakeUser(Plan.INDIVIDUAL), prompts) == prompts

    def test_preserves_order(self, paywall_on):
        prompts = [{"text": f"q{i}"} for i in range(20)]
        capped = cap_prompts(_FakeUser(Plan.INDIVIDUAL), prompts)
        assert [p["text"] for p in capped] == ["q0", "q1", "q2", "q3", "q4"]


@pytest.mark.django_db
class TestAutoScanIsGated:
    """The Prompts-page auto-scan must honour the same limits as the modal."""

    def _make_user_and_site(self):
        from apps.accounts.tests.factories import UserFactory
        from apps.websites.tests.factories import WebsiteFactory

        user = UserFactory()
        return user, WebsiteFactory(user=user)

    def test_spend_cap_blocks_auto_scan(self):
        """Regression: this path had no spend-cap check at all."""
        from apps.llm_ranking.models import LLMRankingAudit
        from apps.prompt_library.api.v1.views import WebsitePromptCreateView

        user, website = self._make_user_and_site()
        user.monthly_ai_cost_cap_usd = 5.0
        user.save(update_fields=["monthly_ai_cost_cap_usd"])

        before = LLMRankingAudit.objects.count()
        with patch("core.ai_tracking.month_to_date_cost", return_value=99.0):
            result = WebsitePromptCreateView._trigger_scan(
                website, user, ["best crm?"], "",
            )

        assert isinstance(result, dict)
        assert result["blocked"] == "monthly_ai_cost_cap_exceeded"
        assert LLMRankingAudit.objects.count() == before, (
            "a blocked scan must not create an audit row"
        )

    def test_auto_scan_caps_prompts_to_plan(self, settings):
        """Regression: bulk upload could queue hundreds of prompts uncapped."""
        from apps.llm_ranking.models import LLMRankingAudit
        from apps.prompt_library.api.v1.views import WebsitePromptCreateView

        settings.PAYWALL_ENABLED = True
        settings.ANTHROPIC_API_KEY = "test"
        user, website = self._make_user_and_site()

        with patch("apps.llm_ranking.services.scan_dispatch.dispatch_scan"):
            audit_id = WebsitePromptCreateView._trigger_scan(
                website, user, [f"question {i}?" for i in range(200)], "",
            )

        assert not isinstance(audit_id, dict), f"scan was blocked: {audit_id}"
        audit = LLMRankingAudit.objects.get(id=audit_id)
        assert len(audit.prompts) == 5, (
            f"200 prompts should truncate to the Individual cap, got {len(audit.prompts)}"
        )

    def test_auto_scan_respects_providers_allowed(self, settings):
        """Regression: this path selected every provider with a configured key."""
        from apps.llm_ranking.models import LLMRankingAudit
        from apps.prompt_library.api.v1.views import WebsitePromptCreateView

        settings.PAYWALL_ENABLED = True
        settings.ANTHROPIC_API_KEY = "test"
        settings.OPENAI_API_KEY = "test"
        settings.GEMINI_API_KEY = "test"
        settings.PERPLEXITY_API_KEY = "test"
        settings.XAI_API_KEY = "test"
        user, website = self._make_user_and_site()

        with patch("apps.llm_ranking.services.scan_dispatch.dispatch_scan"):
            audit_id = WebsitePromptCreateView._trigger_scan(
                website, user, ["best crm?"], "",
            )

        assert not isinstance(audit_id, dict), f"scan was blocked: {audit_id}"
        audit = LLMRankingAudit.objects.get(id=audit_id)
        assert set(audit.providers_queried) <= {"claude", "gpt4"}, (
            f"Individual plan got {audit.providers_queried}"
        )

    def test_dispatch_failure_is_reported_not_swallowed(self, settings):
        """A scan that didn't run must say so rather than look successful."""
        from apps.prompt_library.api.v1.views import WebsitePromptCreateView

        settings.ANTHROPIC_API_KEY = "test"
        user, website = self._make_user_and_site()

        with patch(
            "apps.llm_ranking.services.scan_dispatch.dispatch_scan",
            side_effect=RuntimeError("broker down"),
        ):
            result = WebsitePromptCreateView._trigger_scan(
                website, user, ["best crm?"], "",
            )

        assert isinstance(result, dict)
        assert result["blocked"] == "scan_dispatch_failed"
