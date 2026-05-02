"""
Asserts the Haiku extraction service caps list sizes so a malformed or
hostile LLM response cannot blow up the size of an LLMRankingResult row.

Patches ``_call_haiku`` directly to return a canned JSON string — that
way the test never imports the anthropic SDK and never hits the network.
"""
import json
from unittest.mock import patch

from apps.llm_ranking.services import extraction_service
from apps.llm_ranking.services.extraction_service import HaikuExtractionService


def _patch_haiku(payload: dict):
    return patch.object(
        extraction_service, "_call_haiku",
        return_value=json.dumps(payload),
    )


class TestExtractionCaps:
    def test_caps_competitors_at_50(self):
        oversize = {
            "target_mentioned": True,
            "target_position": 1,
            "target_linked": False,
            "target_sentiment": "positive",
            "target_context": "x",
            "competitors_mentioned": [
                {"name": f"Brand{i}", "position": i, "linked": False}
                for i in range(500)
            ],
            "primary_recommendation": None,
            "citations": [],
        }
        with _patch_haiku(oversize):
            out = HaikuExtractionService.extract(
                response_text="any", brand_name="Target", keywords=[],
            )
        assert len(out["competitors_mentioned"]) <= 50

    def test_caps_citations_at_50(self):
        oversize = {
            "target_mentioned": False,
            "target_position": None,
            "target_linked": False,
            "target_sentiment": "not_mentioned",
            "target_context": "",
            "competitors_mentioned": [],
            "primary_recommendation": None,
            "citations": [f"https://example.com/{i}" for i in range(200)],
        }
        with _patch_haiku(oversize):
            out = HaikuExtractionService.extract(
                response_text="any", brand_name="Target", keywords=[],
            )
        assert len(out["citations"]) <= 50

    def test_truncates_long_citation_url(self):
        long_url = "https://example.com/" + ("x" * 5000)
        payload = {
            "target_mentioned": False,
            "target_position": None,
            "target_linked": False,
            "target_sentiment": "not_mentioned",
            "target_context": "",
            "competitors_mentioned": [],
            "primary_recommendation": None,
            "citations": [long_url],
        }
        with _patch_haiku(payload):
            out = HaikuExtractionService.extract(
                response_text="any", brand_name="Target", keywords=[],
            )
        assert len(out["citations"]) == 1
        assert len(out["citations"][0]) <= 500

    def test_truncates_long_competitor_name(self):
        payload = {
            "target_mentioned": True,
            "target_position": 1,
            "target_linked": False,
            "target_sentiment": "positive",
            "target_context": "",
            "competitors_mentioned": [
                {"name": "X" * 5000, "position": 1, "linked": False},
            ],
            "primary_recommendation": None,
            "citations": [],
        }
        with _patch_haiku(payload):
            out = HaikuExtractionService.extract(
                response_text="any", brand_name="Target", keywords=[],
            )
        assert len(out["competitors_mentioned"][0]["name"]) <= 200

    def test_skips_non_dict_competitor_entries(self):
        payload = {
            "target_mentioned": False,
            "target_position": None,
            "target_linked": False,
            "target_sentiment": "not_mentioned",
            "target_context": "",
            "competitors_mentioned": ["just a string", 42, None],
            "primary_recommendation": None,
            "citations": [],
        }
        with _patch_haiku(payload):
            out = HaikuExtractionService.extract(
                response_text="any", brand_name="Target", keywords=[],
            )
        assert out["competitors_mentioned"] == []
