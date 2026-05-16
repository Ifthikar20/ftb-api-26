"""
Rank-aware GEO ROI bucketing.

Backs the "high-ROI sources to optimize first" framing on the Source
Influence page, which prioritizes content rewrites for sources that are
CITED in LLM responses but RANK LOW in Google search. Per Aggarwal et
al. 2024 (KDD '24, Table 2), GEO content rewrites lift rank-4/5 sources
by up to ~115% while rank-1 sources tend to LOSE visibility from the
same rewrites.
"""
from apps.llm_ranking.tasks import _geo_roi_bucket


def test_rank_1_is_low_roi():
    # Already winning — paper shows GEO rewrites HURT here.
    assert _geo_roi_bucket(1) == "low"


def test_ranks_2_and_3_are_medium():
    assert _geo_roi_bucket(2) == "medium"
    assert _geo_roi_bucket(3) == "medium"


def test_rank_4_plus_is_high():
    assert _geo_roi_bucket(4) == "high"
    assert _geo_roi_bucket(5) == "high"
    assert _geo_roi_bucket(10) == "high"


def test_unranked_treated_as_high_roi():
    # Below Google's top results = invisible = biggest upside.
    assert _geo_roi_bucket(None) == "high"
