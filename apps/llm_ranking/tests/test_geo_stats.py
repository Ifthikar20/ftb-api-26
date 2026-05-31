"""Tests for the GEO KPI builder used by the dashboard Analytics tab."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.llm_ranking.models import LLMRankingAudit, LLMRankingResult
from apps.llm_ranking.services.geo_stats import PERIOD_DAYS, build_kpis_for_user
from apps.llm_ranking.tests.factories import (
    LLMRankingAuditFactory,
    LLMRankingResultFactory,
)


def _by_label(tiles, label):
    return next(t for t in tiles if t["label"] == label)


@pytest.mark.django_db
class TestBuildKpisForUser:
    def test_returns_none_when_user_has_no_completed_audits(self):
        user = UserFactory()
        LLMRankingAuditFactory(created_by=user, status=LLMRankingAudit.STATUS_PENDING)
        assert build_kpis_for_user(user) is None

    def test_returns_three_tiles_in_order(self):
        user = UserFactory()
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=42.0, avg_mention_rank=3.0, completed_at=timezone.now(),
        )
        tiles = build_kpis_for_user(user)
        assert [t["label"] for t in tiles] == ["Visibility", "Position", "Sentiment"]

    def test_visibility_value_reflects_current_period(self):
        user = UserFactory()
        now = timezone.now()
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=60.0, avg_mention_rank=2.0, completed_at=now,
        )
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=40.0, avg_mention_rank=4.0, completed_at=now,
        )
        tiles = build_kpis_for_user(user)
        assert _by_label(tiles, "Visibility")["value"] == "50.0%"
        assert _by_label(tiles, "Position")["value"] == "3.0"

    def test_position_direction_inverts_higher_is_worse(self):
        """A lower avg rank vs. the previous period is an 'up' trend."""
        user = UserFactory()
        now = timezone.now()
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=20.0, avg_mention_rank=5.0,
            completed_at=now - timedelta(days=PERIOD_DAYS + 5),
        )
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=20.0, avg_mention_rank=2.0, completed_at=now,
        )
        tile = _by_label(build_kpis_for_user(user), "Position")
        assert tile["direction"] == "up"
        assert tile["trendNote"] == "Trending up"

    def test_sentiment_score_from_mention_distribution(self):
        user = UserFactory()
        audit = LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=80.0, completed_at=timezone.now(),
        )
        for _ in range(3):
            LLMRankingResultFactory(
                audit=audit, query_succeeded=True, is_mentioned=True,
                sentiment=LLMRankingResult.SENTIMENT_POSITIVE,
            )
        LLMRankingResultFactory(
            audit=audit, query_succeeded=True, is_mentioned=True,
            sentiment=LLMRankingResult.SENTIMENT_NEGATIVE,
        )
        # 3 positive, 1 negative, 4 total -> 50 + 50 * (3-1)/4 = 75
        assert _by_label(build_kpis_for_user(user), "Sentiment")["value"] == "75"

    def test_missing_previous_period_yields_neutral_change(self):
        user = UserFactory()
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=42.0, avg_mention_rank=3.0, completed_at=timezone.now(),
        )
        tile = _by_label(build_kpis_for_user(user), "Visibility")
        assert tile["change"] == "—"
        assert tile["trendNote"] == "No prior period to compare"

    def test_other_users_audits_excluded(self):
        user = UserFactory()
        stranger = UserFactory()
        LLMRankingAuditFactory(
            created_by=stranger, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=99.0, completed_at=timezone.now(),
        )
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=10.0, completed_at=timezone.now(),
        )
        tile = _by_label(build_kpis_for_user(user), "Visibility")
        assert tile["value"] == "10.0%"
