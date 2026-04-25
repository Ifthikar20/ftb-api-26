"""Tests for DiscoveryService.suggest — the real LLM-backed competitor
suggestion path that the onboarding wizard depends on."""
from unittest.mock import patch

from django.test import override_settings

from apps.competitors.services.discovery_service import DiscoveryService


class TestDiscoveryServiceSuggest:

    @override_settings(ANTHROPIC_API_KEY="")
    def test_returns_empty_when_api_key_missing(self):
        result = DiscoveryService.suggest(
            name="Acme", industry="SaaS analytics", url="acme.com",
        )
        assert result == []

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_returns_empty_when_no_business_context(self):
        result = DiscoveryService.suggest(name="", industry="", url="")
        assert result == []

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_parses_well_formed_response(self):
        from apps.competitors.services import discovery_service as svc
        fake = (
            '[{"name": "Mixpanel", "domain": "mixpanel.com", "reason": "Direct"}, '
            ' {"name": "Amplitude", "domain": "amplitude.com", "reason": "Same space"}]'
        )
        with patch.object(svc, "_call_haiku_for_suggestions", return_value=fake):
            result = svc.DiscoveryService.suggest(
                name="Acme", industry="SaaS analytics", url="acme.com",
            )
        assert len(result) == 2
        assert result[0]["name"] == "Mixpanel"
        assert result[0]["domain"] == "mixpanel.com"
        assert result[0]["reason"] == "Direct"

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_normalises_domains(self):
        from apps.competitors.services import discovery_service as svc
        fake = (
            '[{"name": "Mixpanel", "domain": "https://www.mixpanel.com/products/"},'
            ' {"name": "Amplitude", "domain": "WWW.amplitude.com"}]'
        )
        with patch.object(svc, "_call_haiku_for_suggestions", return_value=fake):
            result = svc.DiscoveryService.suggest(
                name="Acme", industry="SaaS",
            )
        assert result[0]["domain"] == "mixpanel.com"
        assert result[1]["domain"] == "amplitude.com"

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_dedupes_competitors_by_domain(self):
        from apps.competitors.services import discovery_service as svc
        fake = (
            '[{"name": "Mixpanel", "domain": "mixpanel.com"},'
            ' {"name": "Mixpanel Inc", "domain": "mixpanel.com"},'   # dupe domain
            ' {"name": "Heap", "domain": "heap.io"}]'
        )
        with patch.object(svc, "_call_haiku_for_suggestions", return_value=fake):
            result = svc.DiscoveryService.suggest(name="Acme", industry="SaaS")
        domains = [r["domain"] for r in result]
        assert domains == ["mixpanel.com", "heap.io"]

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_drops_entries_missing_name_or_domain(self):
        from apps.competitors.services import discovery_service as svc
        fake = (
            '[{"name": "Mixpanel", "domain": "mixpanel.com"},'
            ' {"name": "", "domain": "blank.com"},'              # dropped: empty name
            ' {"name": "NoDomain"},'                              # dropped: no domain
            ' "not a dict",'                                      # dropped: wrong type
            ' {"name": "Heap", "domain": "heap.io"}]'
        )
        with patch.object(svc, "_call_haiku_for_suggestions", return_value=fake):
            result = svc.DiscoveryService.suggest(name="Acme", industry="SaaS")
        assert len(result) == 2
        assert {r["name"] for r in result} == {"Mixpanel", "Heap"}

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_caps_results_at_seven(self):
        from apps.competitors.services import discovery_service as svc
        # Generate 10 entries; service should cap at 7.
        entries = [
            {"name": f"Brand{i}", "domain": f"brand{i}.com"} for i in range(10)
        ]
        import json
        with patch.object(svc, "_call_haiku_for_suggestions", return_value=json.dumps(entries)):
            result = svc.DiscoveryService.suggest(name="Acme", industry="SaaS")
        assert len(result) == 7

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_returns_empty_when_response_is_unparseable(self):
        from apps.competitors.services import discovery_service as svc
        with patch.object(svc, "_call_haiku_for_suggestions", return_value="not json"):
            result = svc.DiscoveryService.suggest(name="Acme", industry="SaaS")
        assert result == []

    @override_settings(ANTHROPIC_API_KEY="dummy")
    def test_returns_empty_when_call_raises(self):
        from apps.competitors.services import discovery_service as svc
        with patch.object(svc, "_call_haiku_for_suggestions", side_effect=RuntimeError("api down")):
            result = svc.DiscoveryService.suggest(name="Acme", industry="SaaS")
        assert result == []
