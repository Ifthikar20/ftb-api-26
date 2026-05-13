"""
Impression metrics — Position-Adjusted Word Count (eq. 3), Word Count
(eq. 2), and Relative Improvement (eq. 4) from Aggarwal et al. 2024
"GEO: Generative Engine Optimization" (KDD '24, arXiv:2311.09735v3).
"""
import math

import pytest

from apps.llm_ranking.services import impression


# ── Imp_pwc (eq. 3) ──────────────────────────────────────────────────────

def test_empty_response_returns_zero_for_requested_indices():
    out = impression.position_adjusted_word_counts("", source_indices=[1, 2])
    assert out == {1: 0.0, 2: 0.0}


def test_uncited_source_scores_zero():
    text = "First sentence with no citation. Second sentence [1]."
    out = impression.position_adjusted_word_counts(text, source_indices=[1, 2])
    assert out[2] == 0.0
    assert out[1] > 0


def test_single_cited_sentence_matches_hand_computed_value():
    # One sentence, 5 words, position 0 of 1 sentences.
    # decay = exp(-0/1) = 1.0, contribution = 5 * 1 = 5
    # total words = 5, score = 5/5 = 1.0
    text = "Alpha beta gamma delta epsilon [1]."
    out = impression.position_adjusted_word_counts(text, source_indices=[1])
    assert out[1] == pytest.approx(1.0)


def test_earlier_sentence_outscores_later_at_same_word_count():
    """Core finding the paper bakes into eq. 3: position matters."""
    text = (
        "Aa bb cc dd ee ff [1]. "   # pos 0, 6 words, cites [1]
        "Filler one. Filler two. "  # pos 1, 2; no citations
        "Aa bb cc dd ee ff [2]."    # pos 3, 6 words, cites [2]
    )
    out = impression.position_adjusted_word_counts(text, source_indices=[1, 2])
    assert out[1] > out[2]


def test_multi_citation_split_between_sources():
    """[1, 2] in one sentence should credit both sources equally."""
    text = "Shared sentence with both citations [1, 2]."
    out = impression.position_adjusted_word_counts(text, source_indices=[1, 2])
    assert out[1] == pytest.approx(out[2])
    assert out[1] > 0


def test_adjacent_brackets_parsed_as_two_citations():
    text = "Adjacent style citation [1][2]."
    out = impression.position_adjusted_word_counts(text, source_indices=[1, 2])
    assert out[1] > 0 and out[2] > 0
    assert out[1] == pytest.approx(out[2])


def test_score_is_normalized_into_zero_one_range():
    text = (
        "Sentence one cites the source [1]. "
        "Sentence two also cites the source [1]. "
        "Sentence three does not cite anything."
    )
    out = impression.position_adjusted_word_counts(text, source_indices=[1])
    # Sum of weights can never exceed sum of words; ratio ≤ 1.
    assert 0 < out[1] <= 1.0


def test_decay_matches_paper_formula_exactly():
    # Two sentences, 3 words each. First cites [1], second cites [2].
    # pos 0: weight = 3 * exp(-0/2) = 3.0
    # pos 1: weight = 3 * exp(-1/2) ≈ 1.8195
    # total words = 6
    text = "One two three [1]. Four five six [2]."
    out = impression.position_adjusted_word_counts(text, source_indices=[1, 2])
    assert out[1] == pytest.approx(3.0 / 6.0)
    assert out[2] == pytest.approx((3.0 * math.exp(-1 / 2)) / 6.0)


def test_citation_markers_dont_inflate_word_count():
    """`[1] [2]` shouldn't count as 2 words toward |s|."""
    text_a = "Real words here [1]."
    text_b = "Real words here [1] [2] [3] [4] [5]."
    a = impression.position_adjusted_word_counts(text_a, source_indices=[1])
    b = impression.position_adjusted_word_counts(text_b, source_indices=[1])
    # Same 3 real words, same position, same denominator → same score.
    assert a[1] == pytest.approx(b[1])


# ── Word Count baseline (eq. 2) ──────────────────────────────────────────

def test_word_count_metric_ignores_position():
    text = "Aa bb cc dd ee ff [1]. Filler. Aa bb cc dd ee ff [2]."
    out = impression.word_count_impression(text, source_indices=[1, 2])
    # Same word counts → same WC score, regardless of position.
    assert out[1] == pytest.approx(out[2])


# ── Relative improvement (eq. 4) ─────────────────────────────────────────

def test_relative_improvement_positive_lift():
    # 0.20 -> 0.30 = +50%
    assert impression.relative_improvement(0.20, 0.30) == pytest.approx(50.0)


def test_relative_improvement_negative_lift():
    assert impression.relative_improvement(0.40, 0.30) == pytest.approx(-25.0)


def test_relative_improvement_zero_baseline_is_undefined():
    assert impression.relative_improvement(0.0, 0.30) is None
    assert impression.relative_improvement(-0.1, 0.30) is None


def test_relative_improvement_none_inputs():
    assert impression.relative_improvement(None, 0.3) is None
    assert impression.relative_improvement(0.3, None) is None


# ── Projected lift table (Table 1) ───────────────────────────────────────

def test_known_methods_have_positive_projected_lift():
    assert impression.projected_lift("quotation_addition") > 0
    assert impression.projected_lift("statistics_addition") > 0
    assert impression.projected_lift("cite_sources") > 0


def test_keyword_stuffing_is_flagged_as_regression():
    # Paper Section 4 — keyword stuffing actively HURTS visibility.
    assert impression.projected_lift("keyword_stuffing") < 0


def test_unknown_method_returns_none():
    assert impression.projected_lift("nonsense") is None
    assert impression.projected_lift("") is None


# ── Domain → method map (Table 3) ────────────────────────────────────────

def test_domain_map_matches_paper_table_3():
    assert impression.best_method_for_domain("Debate") == "authoritative"
    assert impression.best_method_for_domain("Business") == "fluency_optimization"
    assert impression.best_method_for_domain("Facts") == "cite_sources"
    assert impression.best_method_for_domain("History") == "quotation_addition"
    assert impression.best_method_for_domain("Opinion") == "statistics_addition"


def test_unknown_domain_falls_back_to_best_overall():
    # Paper's overall winner is Quotation Addition (+41% avg).
    assert impression.best_method_for_domain(None) == "quotation_addition"
    assert impression.best_method_for_domain("") == "quotation_addition"
    assert impression.best_method_for_domain("xyz") == "quotation_addition"
