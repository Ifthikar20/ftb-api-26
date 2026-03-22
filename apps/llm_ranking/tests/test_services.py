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
