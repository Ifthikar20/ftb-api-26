"""Tests for LLM Ranking service logic."""
from unittest.mock import MagicMock, patch

import pytest

from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
from apps.llm_ranking.services.ranking_service import LLMRankingService
from apps.llm_ranking.tests.factories import LLMRankingAuditFactory, LLMRankingResultFactory

# ── Mention analysis ──────────────────────────────────────────────────────────

class TestAnalyzeMention:
    def test_detects_mention_by_business_name(self):
        result = LLMRankingService._analyze_mention(
            response_text="We recommend Acme SaaS for its great dashboard.",
            business_name="Acme SaaS",
            keywords=[],
        )
        assert result["is_mentioned"] is True

    def test_detects_mention_by_keyword(self):
        result = LLMRankingService._analyze_mention(
            response_text="The best analytics tool on the market is...",
            business_name="Acme SaaS",
            keywords=["analytics"],
        )
        assert result["is_mentioned"] is True

    def test_no_mention(self):
        result = LLMRankingService._analyze_mention(
            response_text="We recommend Competitor X and Competitor Y.",
            business_name="Acme SaaS",
            keywords=["acme"],
        )
        assert result["is_mentioned"] is False
        assert result["sentiment"] == "not_mentioned"
        assert result["mention_rank"] is None

    def test_detects_rank_from_numbered_list(self):
        response = (
            "1. Competitor X — fast\n"
            "2. Acme SaaS — great analytics\n"
            "3. Competitor Y — cheap\n"
        )
        result = LLMRankingService._analyze_mention(
            response_text=response,
            business_name="Acme SaaS",
            keywords=[],
        )
        assert result["is_mentioned"] is True
        assert result["mention_rank"] == 2

    def test_detects_rank_position_one(self):
        response = "1. Acme SaaS — top pick\n2. Others"
        result = LLMRankingService._analyze_mention(
            response_text=response,
            business_name="Acme SaaS",
            keywords=[],
        )
        assert result["mention_rank"] == 1

    def test_positive_sentiment_detected(self):
        result = LLMRankingService._analyze_mention(
            response_text="Acme SaaS is the best and most recommended tool.",
            business_name="Acme SaaS",
            keywords=[],
        )
        assert result["sentiment"] == "positive"

    def test_negative_sentiment_detected(self):
        result = LLMRankingService._analyze_mention(
            response_text="Acme SaaS is expensive and difficult to use.",
            business_name="Acme SaaS",
            keywords=[],
        )
        assert result["sentiment"] == "negative"

    def test_case_insensitive_match(self):
        result = LLMRankingService._analyze_mention(
            response_text="ACME SAAS is popular.",
            business_name="Acme SaaS",
            keywords=[],
        )
        assert result["is_mentioned"] is True


# ── Score computation ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestComputeOverallScore:
    def test_empty_results_returns_zero(self):
        scores = LLMRankingService.compute_overall_score([])
        assert scores["overall_score"] == 0
        assert scores["mention_rate"] == 0.0

    def test_all_mentioned_rank_1_gives_high_score(self):
        audit = LLMRankingAuditFactory()
        results = [
            LLMRankingResultFactory(
                audit=audit,
                provider=p,
                is_mentioned=True,
                mention_rank=1,
                sentiment=LLMRankingResult.SENTIMENT_POSITIVE,
                query_succeeded=True,
            )
            for p in ["claude", "gpt4", "gemini"]
        ]
        scores = LLMRankingService.compute_overall_score(results)
        assert scores["overall_score"] >= 70
        assert scores["mention_rate"] == 100.0

    def test_no_mentions_gives_low_score(self):
        audit = LLMRankingAuditFactory()
        results = [
            LLMRankingResultFactory(
                audit=audit,
                provider="claude",
                is_mentioned=False,
                mention_rank=None,
                sentiment=LLMRankingResult.SENTIMENT_NOT_MENTIONED,
                query_succeeded=True,
            )
        ]
        scores = LLMRankingService.compute_overall_score(results)
        assert scores["overall_score"] < 20
        assert scores["mention_rate"] == 0.0

    def test_failed_queries_excluded_from_mention_rate(self):
        audit = LLMRankingAuditFactory()
        results = [
            LLMRankingResultFactory(audit=audit, provider="claude", query_succeeded=False),
            LLMRankingResultFactory(
                audit=audit, provider="gpt4",
                is_mentioned=True, query_succeeded=True, mention_rank=1,
                sentiment=LLMRankingResult.SENTIMENT_POSITIVE,
            ),
        ]
        scores = LLMRankingService.compute_overall_score(results)
        # Only 1 succeeded, 1 mentioned → 100% mention rate for succeeded
        assert scores["mention_rate"] == 100.0

    def test_score_capped_at_100(self):
        audit = LLMRankingAuditFactory()
        results = [
            LLMRankingResultFactory(
                audit=audit, provider=p,
                is_mentioned=True, mention_rank=1,
                sentiment=LLMRankingResult.SENTIMENT_POSITIVE,
                query_succeeded=True,
            )
            for p in ["claude", "gpt4", "gemini", "perplexity"]
        ]
        scores = LLMRankingService.compute_overall_score(results)
        assert scores["overall_score"] <= 100


# ── run_audit integration (mocked providers) ─────────────────────────────────

@pytest.mark.django_db
class TestRunAudit:
    def _mock_providers(self):
        return {
            "apps.llm_ranking.services.ranking_service.LLMRankingService._query_claude":
                MagicMock(return_value=(True, "1. Acme SaaS — recommended\n2. Others", "")),
            "apps.llm_ranking.services.ranking_service.LLMRankingService._query_openai":
                MagicMock(return_value=(False, "", "OPENAI_API_KEY not configured")),
            "apps.llm_ranking.services.ranking_service.LLMRankingService._query_gemini":
                MagicMock(return_value=(False, "", "GEMINI_API_KEY not configured")),
            "apps.llm_ranking.services.ranking_service.LLMRankingService._query_perplexity":
                MagicMock(return_value=(False, "", "PERPLEXITY_API_KEY not configured")),
        }

    def test_run_audit_completes(self):
        audit = LLMRankingAuditFactory(
            business_name="Acme SaaS",
            keywords=["acme"],
            prompts=["What is the best SaaS tool?"],
        )
        with patch.multiple("apps.llm_ranking.services.ranking_service.LLMRankingService",
                            _query_claude=MagicMock(return_value=(True, "1. Acme SaaS is great\n2. Others", "")),
                            _query_openai=MagicMock(return_value=(False, "", "no key")),
                            _query_gemini=MagicMock(return_value=(False, "", "no key")),
                            _query_perplexity=MagicMock(return_value=(False, "", "no key"))):
            LLMRankingService.run_audit(audit_id=str(audit.id))

        audit.refresh_from_db()
        assert audit.status == LLMRankingAudit.STATUS_COMPLETED
        assert audit.overall_score >= 0
        assert audit.results.count() == 4  # 4 providers × 1 prompt

    def test_run_audit_marks_failed_on_exception(self):
        audit = LLMRankingAuditFactory(prompts=["test?"])
        with patch("apps.llm_ranking.services.ranking_service.LLMRankingService._query_claude",
                   side_effect=Exception("unexpected error")):
            with patch("apps.llm_ranking.services.ranking_service.LLMRankingService._query_openai",
                       return_value=(False, "", "no key")), \
                 patch("apps.llm_ranking.services.ranking_service.LLMRankingService._query_gemini",
                       return_value=(False, "", "no key")), \
                 patch("apps.llm_ranking.services.ranking_service.LLMRankingService._query_perplexity",
                       return_value=(False, "", "no key")):
                # Should not raise — exception is caught per-provider
                LLMRankingService.run_audit(audit_id=str(audit.id))

        audit.refresh_from_db()
        # Audit still completes even if one provider errors
        assert audit.status == LLMRankingAudit.STATUS_COMPLETED

    def test_run_audit_stores_mention_correctly(self):
        audit = LLMRankingAuditFactory(
            business_name="Acme SaaS",
            keywords=["acme"],
            prompts=["Best tool?"],
        )
        with patch.multiple("apps.llm_ranking.services.ranking_service.LLMRankingService",
                            _query_claude=MagicMock(return_value=(True, "1. Acme SaaS tops the list", "")),
                            _query_openai=MagicMock(return_value=(False, "", "no key")),
                            _query_gemini=MagicMock(return_value=(False, "", "no key")),
                            _query_perplexity=MagicMock(return_value=(False, "", "no key"))):
            LLMRankingService.run_audit(audit_id=str(audit.id))

        result = LLMRankingResult.objects.get(
            audit=audit, provider=LLMRankingResult.PROVIDER_CLAUDE
        )
        assert result.is_mentioned is True
        assert result.query_succeeded is True


# ── Recommendations ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecommendations:
    def test_low_score_gives_content_recommendation(self):
        audit = LLMRankingAuditFactory(
            status=LLMRankingAudit.STATUS_COMPLETED,
            overall_score=15,
            mention_rate=10.0,
            avg_mention_rank=0.0,
        )
        recs = LLMRankingService.generate_recommendations(audit=audit)
        assert len(recs) >= 1
        combined = " ".join(recs).lower()
        assert "content" in combined or "mentioned" in combined or "publish" in combined

    def test_high_score_gives_maintenance_recommendation(self):
        audit = LLMRankingAuditFactory(
            status=LLMRankingAudit.STATUS_COMPLETED,
            overall_score=80,
            mention_rate=85.0,
            avg_mention_rank=1.5,
        )
        recs = LLMRankingService.generate_recommendations(audit=audit)
        combined = " ".join(recs).lower()
        assert "maintain" in combined or "strong" in combined or "content" in combined

    def test_high_rank_gives_position_recommendation(self):
        audit = LLMRankingAuditFactory(
            status=LLMRankingAudit.STATUS_COMPLETED,
            overall_score=50,
            mention_rate=70.0,
            avg_mention_rank=7.0,
        )
        recs = LLMRankingService.generate_recommendations(audit=audit)
        combined = " ".join(recs).lower()
        assert "rank" in combined or "position" in combined or "authority" in combined


# ── Wilson CI helper ──────────────────────────────────────────────────────────

class TestWilsonCI:
    def test_zero_sample_returns_zeros(self):
        from apps.llm_ranking.services.ranking_service import wilson_ci
        lower, upper = wilson_ci(0, 0)
        assert lower == 0.0
        assert upper == 0.0

    def test_all_successes_has_upper_at_one(self):
        from apps.llm_ranking.services.ranking_service import wilson_ci
        lower, upper = wilson_ci(10, 10)
        assert upper == 1.0
        assert lower < 1.0  # Wilson keeps lower away from 1 even for perfect success

    def test_all_failures_has_lower_at_zero(self):
        from apps.llm_ranking.services.ranking_service import wilson_ci
        lower, upper = wilson_ci(0, 10)
        assert lower == 0.0
        assert upper > 0.0

    def test_small_sample_wider_than_large_sample(self):
        from apps.llm_ranking.services.ranking_service import wilson_ci
        l_small, u_small = wilson_ci(3, 10)
        l_large, u_large = wilson_ci(300, 1000)
        # Both point estimates equal 0.3, but CI shrinks as N grows.
        assert (u_small - l_small) > (u_large - l_large)

    def test_half_proportion_centres_around_half(self):
        from apps.llm_ranking.services.ranking_service import wilson_ci
        lower, upper = wilson_ci(50, 100)
        # Expected Wilson CI on 50/100 is approx [0.404, 0.596]
        assert 0.38 < lower < 0.42
        assert 0.58 < upper < 0.62


@pytest.mark.django_db
class TestComputeOverallScoreCI:
    def test_mention_rate_ci_is_returned(self):
        audit = LLMRankingAuditFactory()
        results = [
            LLMRankingResultFactory(
                audit=audit, provider="claude",
                is_mentioned=(i % 2 == 0), query_succeeded=True,
                mention_rank=1 if (i % 2 == 0) else None,
                sentiment=(LLMRankingResult.SENTIMENT_POSITIVE if (i % 2 == 0)
                           else LLMRankingResult.SENTIMENT_NOT_MENTIONED),
            )
            for i in range(10)
        ]
        scores = LLMRankingService.compute_overall_score(results)
        assert "mention_rate_ci_lower" in scores
        assert "mention_rate_ci_upper" in scores
        assert scores["mention_rate"] == 50.0
        assert scores["mention_rate_ci_lower"] < 50.0 < scores["mention_rate_ci_upper"]


# ── Haiku extraction service ──────────────────────────────────────────────────

class TestHaikuExtractionService:
    def test_returns_empty_result_for_blank_input(self):
        from apps.llm_ranking.services.extraction_service import HaikuExtractionService
        result = HaikuExtractionService.extract(
            response_text="", brand_name="Acme SaaS", keywords=["analytics"],
        )
        assert result["is_mentioned"] is False
        assert result["competitors_mentioned"] == []
        assert result["citations"] == []

    def test_falls_back_to_heuristic_when_llm_call_fails(self):
        from apps.llm_ranking.services import extraction_service as svc
        with patch.object(svc, "_call_haiku", side_effect=RuntimeError("boom")):
            result = svc.HaikuExtractionService.extract(
                response_text="1. Acme SaaS — great analytics platform\n2. Other tool",
                brand_name="Acme SaaS",
                keywords=["analytics"],
            )
        assert result["is_mentioned"] is True
        assert result["mention_rank"] == 1
        assert result["extraction_model"] == "heuristic"

    def test_successful_extraction_normalises_payload(self):
        from apps.llm_ranking.services import extraction_service as svc
        fake_json = (
            '{"target_mentioned": true, "target_position": 2, "target_linked": true, '
            '"target_sentiment": "positive", "target_context": "Acme SaaS is great", '
            '"competitors_mentioned": ['
            '  {"name": "Mixpanel", "position": 1, "linked": false},'
            '  {"name": "", "position": 3, "linked": false},'   # dropped: empty name
            '  "not a dict"'                                    # dropped: wrong type
            '], '
            '"primary_recommendation": "Mixpanel", '
            '"citations": ["https://g2.com/x", "not-a-url"]}'
        )
        with patch.object(svc, "_call_haiku", return_value=fake_json):
            result = svc.HaikuExtractionService.extract(
                response_text="irrelevant",
                brand_name="Acme SaaS",
                keywords=[],
            )
        assert result["is_mentioned"] is True
        assert result["mention_rank"] == 2
        assert result["is_linked"] is True
        assert result["sentiment"] == "positive"
        assert len(result["competitors_mentioned"]) == 1
        assert result["competitors_mentioned"][0]["name"] == "Mixpanel"
        assert result["primary_recommendation"] == "Mixpanel"
        assert result["citations"] == ["https://g2.com/x"]
        assert result["extraction_model"] == svc.EXTRACTION_MODEL

    def test_invalid_sentiment_defaults_based_on_mention(self):
        from apps.llm_ranking.services import extraction_service as svc
        fake_json = (
            '{"target_mentioned": false, "target_position": null, "target_linked": false, '
            '"target_sentiment": "garbage", "target_context": "", '
            '"competitors_mentioned": [], "primary_recommendation": null, "citations": []}'
        )
        with patch.object(svc, "_call_haiku", return_value=fake_json):
            result = svc.HaikuExtractionService.extract(
                response_text="x", brand_name="Acme SaaS", keywords=[],
            )
        assert result["sentiment"] == "not_mentioned"


# ── Prompt library ────────────────────────────────────────────────────────────

class TestPromptLibrary:
    def test_generate_returns_dict_list_with_intents(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        prompts = PromptLibrary.generate(industry="SaaS analytics")
        assert len(prompts) > 0
        for p in prompts:
            assert set(p.keys()) == {"text", "intent"}
            assert isinstance(p["text"], str) and p["text"]
            assert isinstance(p["intent"], str) and p["intent"]

    def test_mix_includes_multiple_intents(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        prompts = PromptLibrary.generate(industry="CRM", max_prompts=10)
        intents = {p["intent"] for p in prompts}
        # With 10 prompts we should cover at least 4 distinct intents.
        assert len(intents) >= 4

    def test_location_adds_local_intent(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        local = PromptLibrary.generate(industry="law firm", location="Dallas, TX", max_prompts=10)
        assert any(p["intent"] == "local" for p in local)
        for p in local:
            if p["intent"] == "local":
                assert "Dallas, TX" in p["text"]

    def test_no_location_omits_local_intent(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        prompts = PromptLibrary.generate(industry="analytics", max_prompts=10)
        assert all(p["intent"] != "local" for p in prompts)

    def test_max_prompts_is_respected(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        prompts = PromptLibrary.generate(industry="x", max_prompts=3)
        assert len(prompts) == 3

    def test_generate_texts_returns_unique_strings(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        texts = PromptLibrary.generate_texts(industry="x", max_prompts=10)
        assert len(texts) == len(set(texts))
        assert all(isinstance(t, str) and t for t in texts)

    def test_intents_for_tags_generated_prompts(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        texts = PromptLibrary.generate_texts(industry="design tools", max_prompts=6)
        intents = PromptLibrary.intents_for(texts)
        assert len(intents) == len(texts)
        # Generated prompts should map to real intents, not "custom".
        assert any(i != "custom" for i in intents)

    def test_intents_for_returns_custom_for_unknown_text(self):
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        intents = PromptLibrary.intents_for(["Should I buy a kayak this weekend?"])
        assert intents == ["custom"]
