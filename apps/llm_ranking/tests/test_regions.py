"""Tests for the region prompt-flavor helpers."""
from apps.llm_ranking.services.regions import (
    REGION_GLOBAL,
    REGION_IN,
    REGION_US,
    flavor_prompt,
    get_region,
)


class TestRegionLookup:
    def test_known_region(self):
        r = get_region("us")
        assert r.code == "us"
        assert r.perplexity_country == "US"
        assert r.flavor

    def test_unknown_falls_back_to_global(self):
        assert get_region("zz").code == REGION_GLOBAL
        assert get_region("").code == REGION_GLOBAL
        assert get_region(None).code == REGION_GLOBAL

    def test_uk_maps_to_perplexity_gb(self):
        # UK is the audit-side region code, but Perplexity expects GB.
        assert get_region("uk").perplexity_country == "GB"

    def test_global_has_no_flavor(self):
        assert get_region(REGION_GLOBAL).flavor == ""
        assert get_region(REGION_GLOBAL).perplexity_country == ""


class TestFlavorPrompt:
    def test_global_is_noop(self):
        assert flavor_prompt("Best tools?", REGION_GLOBAL) == "Best tools?"

    def test_question_keeps_question_mark(self):
        flavored = flavor_prompt("What are the best SaaS analytics tools?", REGION_US)
        assert flavored.endswith("?")
        assert "US" in flavored or "for US" in flavored

    def test_statement_keeps_period(self):
        flavored = flavor_prompt("Compare the top 5 platforms.", REGION_IN)
        assert flavored.endswith(".")
        assert "India" in flavored

    def test_unknown_region_is_noop(self):
        text = "Best tools?"
        assert flavor_prompt(text, "zz") == text

    def test_does_not_double_flavor(self):
        # Idempotence isn't strictly required, but the flavour should at least
        # not crash or produce a sentence with two question marks.
        once = flavor_prompt("Best tools?", REGION_IN)
        twice = flavor_prompt(once, REGION_IN)
        assert twice.count("?") == 1
