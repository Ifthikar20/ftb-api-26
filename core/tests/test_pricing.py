"""
Guards on the AI cost ledger.

``core.ai_tracking.PRICING`` is what the per-user monthly spend cap and the
HTTP 402 gate in ``LLMRankingAuditListView`` are computed from. A model that
reaches production without a price entry doesn't fail — it books at the
``default`` rate, so the cap trips at the wrong time and the usage ledger
misreports. These tests exist to make that a CI failure instead.
"""
import pytest

from apps.llm_ranking.providers import (
    MODEL_VARIANTS,
    ClaudeProvider,
    default_variant_for,
)
from core.ai_tracking import PRICING, UNVERIFIED_PRICES, _estimate_cost


class TestPricingCoversVariants:
    def test_pricing_covers_variants(self):
        """Every selectable model must have a price.

        Regression: 7 of 16 variants (Sonnet 4.5, Opus 4.1, Gemini 2.0 Flash,
        Grok 4/3, DeepSeek chat/reasoner) had no entry and silently billed at
        $3/$15. Grok mattered most — it sits in PROVIDERS, the live audit
        router, so real audits were costed from a guess.
        """
        missing = [
            (provider, model_id)
            for provider, variants in MODEL_VARIANTS.items()
            for _label, model_id, _default in variants
            if model_id not in PRICING
        ]
        assert not missing, (
            "Model variants with no PRICING entry — these bill at the "
            f"default rate and corrupt the spend cap: {missing}"
        )

    def test_default_key_is_not_a_selectable_model(self):
        """`default` is the fallback bucket, not something a picker can pick."""
        selectable = {
            model_id
            for variants in MODEL_VARIANTS.values()
            for _label, model_id, _d in variants
        }
        assert "default" not in selectable


class TestClaudeDefaultConsistency:
    def test_default_variant_matches_provider(self):
        """The audit router and the Model Test picker must agree on "claude".

        Regression: ClaudeProvider.DEFAULT_MODEL was claude-haiku-4-5 while
        MODEL_VARIANTS flagged claude-sonnet-4-20250514 as default, so
        get_provider() and default_variant_for() returned different models
        for the same provider key.
        """
        assert default_variant_for("claude") == f"claude:{ClaudeProvider.DEFAULT_MODEL}"

    def test_provider_default_is_priced(self):
        assert ClaudeProvider.DEFAULT_MODEL in PRICING


class TestEstimateCost:
    def test_haiku_45_rate(self):
        """Haiku 4.5 is $1.00/$5.00 per 1M. Was entered as $0.80/$4.00.

        It backs both the default `claude` provider and every extraction
        call, so it is the highest-volume model in the system — a 25%
        understatement here skewed the entire ledger.
        """
        # 1M input + 1M output = 1.00 + 5.00
        assert _estimate_cost("claude-haiku-4-5", 1_000_000, 1_000_000) == 6.00

    def test_known_model_does_not_use_default(self):
        """A priced model must not be costed at the fallback rate."""
        haiku = _estimate_cost("claude-haiku-4-5", 1_000_000, 0)
        fallback = _estimate_cost("nonexistent-model-xyz", 1_000_000, 0)
        assert haiku == 1.00
        assert fallback == 3.00
        assert haiku != fallback

    def test_unknown_model_warns_once(self, caplog):
        """An unpriced model logs rather than mis-billing in silence.

        The CI guard above catches variants; this covers ids injected at
        runtime through LLM_CLAUDE_MODEL / LLM_EXTRACTION_MODEL, which no
        static check can see.
        """
        from core import ai_tracking

        ai_tracking._WARNED_UNPRICED.discard("some-unpriced-model")
        with caplog.at_level("WARNING", logger="core.ai_tracking"):
            _estimate_cost("some-unpriced-model", 1000, 500)
            _estimate_cost("some-unpriced-model", 1000, 500)
        hits = [r for r in caplog.records if "some-unpriced-model" in r.getMessage()]
        assert len(hits) == 1, "should warn once per model name, not per call"

    @pytest.mark.parametrize("model_id", sorted(UNVERIFIED_PRICES))
    def test_unverified_prices_are_still_priced(self, model_id):
        """Unverified beats absent.

        These rates were added from memory — the vendor pricing pages are
        blocked by the build environment's egress proxy. They are much closer
        than the $3/$15 fallback they replace, but this test only asserts an
        entry exists; it does not assert the number is right. Verify against
        the live pricing pages before setting customer rates from this ledger.
        """
        assert model_id in PRICING
        assert PRICING[model_id]["input"] > 0
