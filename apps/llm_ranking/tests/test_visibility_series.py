"""Tests for the visibility-over-time series builder."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.llm_ranking.models import LLMRankingAudit
from apps.llm_ranking.services.visibility_series import (
    DAY_BUCKETS,
    MONTH_BUCKETS,
    WEEK_BUCKETS,
    build_for_user,
)
from apps.llm_ranking.tests.factories import (
    LLMRankingAuditFactory,
    LLMRankingResultFactory,
)


@pytest.mark.django_db
class TestBuildForUser:
    def test_returns_none_when_user_has_no_completed_audits(self):
        user = UserFactory()
        # A pending audit must not flip the gate.
        LLMRankingAuditFactory(created_by=user, status=LLMRankingAudit.STATUS_PENDING)
        assert build_for_user(user) is None

    def test_returns_all_three_resolutions_when_user_has_data(self):
        user = UserFactory()
        LLMRankingAuditFactory(
            created_by=user,
            status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=42.0,
            completed_at=timezone.now(),
        )
        series = build_for_user(user)
        assert set(series) == {"day", "week", "month"}
        assert len(series["day"]["labels"]) == DAY_BUCKETS
        assert len(series["week"]["labels"]) == WEEK_BUCKETS
        assert len(series["month"]["labels"]) == MONTH_BUCKETS
        for res in ("day", "week", "month"):
            assert len(series[res]["brand"]) == len(series[res]["labels"])
            assert len(series[res]["competitor"]) == len(series[res]["labels"])

    def test_brand_series_averages_mention_rate_in_bucket(self):
        user = UserFactory()
        now = timezone.now()
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=40.0, completed_at=now,
        )
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=60.0, completed_at=now,
        )
        series = build_for_user(user)
        # Today's bucket is the last entry in the day series.
        assert series["day"]["brand"][-1] == 50.0

    def test_competitor_rate_is_share_of_answers_with_competitors(self):
        user = UserFactory()
        audit = LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=10.0, completed_at=timezone.now(),
        )
        LLMRankingResultFactory(audit=audit, query_succeeded=True, competitors_mentioned=[])
        LLMRankingResultFactory(
            audit=audit, query_succeeded=True, competitors_mentioned=["Rival"],
        )
        LLMRankingResultFactory(
            audit=audit, query_succeeded=True,
            competitors_mentioned=[{"name": "Rival2", "position": 2}],
        )
        # Failed cell should be ignored entirely.
        LLMRankingResultFactory(
            audit=audit, query_succeeded=False, competitors_mentioned=["Ignored"],
        )
        series = build_for_user(user)
        # 2 of 3 succeeded cells mention a competitor -> 66.7%
        assert series["day"]["competitor"][-1] == pytest.approx(66.7, abs=0.05)

    def test_other_users_audits_are_excluded(self):
        user = UserFactory()
        stranger = UserFactory()
        LLMRankingAuditFactory(
            created_by=stranger, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=99.0, completed_at=timezone.now(),
        )
        # The user themselves has at least one audit so we get a series back.
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=10.0, completed_at=timezone.now() - timedelta(days=3),
        )
        series = build_for_user(user)
        # Today's bucket has no audits for this user -> 0.
        assert series["day"]["brand"][-1] == 0.0

    def test_empty_buckets_report_zero(self):
        user = UserFactory()
        # Only one audit, well in the past — month series should have a non-zero
        # entry only in the matching bucket.
        old = timezone.now() - timedelta(days=120)
        LLMRankingAuditFactory(
            created_by=user, status=LLMRankingAudit.STATUS_COMPLETED,
            mention_rate=30.0, completed_at=old,
        )
        series = build_for_user(user)
        assert series["day"]["brand"] == [0.0] * DAY_BUCKETS
