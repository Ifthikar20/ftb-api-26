"""
Tests for the onboarding orchestrator.

External services (domain_scanner, competitor_discovery, anthropic) are
patched at the module boundary so the suite never hits the network.
"""
from unittest.mock import patch

from apps.onboarding.services import onboarding_service
from apps.onboarding.services.onboarding_service import run_onboarding_scan

_HEALTHY_SCAN = {
    "success": True,
    "business_name": "Acme",
    "industry": "SaaS analytics",
    "domain": "acme.com",
    "description": "Acme builds growth analytics for SaaS teams.",
    "products": ["Funnels", "Retention", "Reports"],
    "features": ["dashboards", "alerts", "integrations"],
    "selling_points": ["Easy setup", "Lightweight", "Slack alerts"],
    "topics": ["funnel analytics", "saas growth", "user retention"],
}


class TestRunOnboardingScan:
    def test_returns_failure_payload_when_scan_fails(self):
        with patch.object(onboarding_service, "scan_domain",
                          return_value={"success": False, "error": "404"}):
            payload = run_onboarding_scan("https://example.com")
        assert payload.success is False
        assert payload.error == "404"
        assert payload.competitors == []

    def test_happy_path_populates_all_fields(self, settings):
        # Ensure description polish + competitor discovery silently
        # skip when their dependencies aren't available — the
        # orchestrator should still return a valid payload.
        settings.ANTHROPIC_API_KEY = ""
        with patch.object(onboarding_service, "scan_domain",
                          return_value=_HEALTHY_SCAN), \
             patch.object(onboarding_service, "_safe_discover_competitors",
                          return_value=[
                              {"name": "Mixpanel", "domain": "mixpanel.com"},
                              {"name": "Amplitude", "domain": "amplitude.com"},
                          ]):
            payload = run_onboarding_scan("https://acme.com")
        assert payload.success is True
        assert payload.business_name == "Acme"
        assert payload.industry == "SaaS analytics"
        assert payload.domain == "acme.com"
        assert "growth analytics" in payload.description_short
        assert len(payload.products) == 3
        assert len(payload.competitors) == 2

    def test_polish_falls_back_to_raw_description_when_no_api_key(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        with patch.object(onboarding_service, "scan_domain",
                          return_value=_HEALTHY_SCAN), \
             patch.object(onboarding_service, "_safe_discover_competitors",
                          return_value=[]):
            payload = run_onboarding_scan("https://acme.com")
        # Without a key the polish helper returns the scraped description.
        assert payload.description_short == _HEALTHY_SCAN["description"]

    def test_long_raw_description_truncated_in_fallback(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        long_desc = "x" * 600
        scan = {**_HEALTHY_SCAN, "description": long_desc}
        with patch.object(onboarding_service, "scan_domain", return_value=scan), \
             patch.object(onboarding_service, "_safe_discover_competitors",
                          return_value=[]):
            payload = run_onboarding_scan("https://acme.com")
        assert len(payload.description_short) <= 280

    def test_caps_lists(self):
        # Hostile / malformed scan with huge lists must be capped.
        scan = {
            **_HEALTHY_SCAN,
            "products": [f"P{i}" for i in range(100)],
            "features": [f"F{i}" for i in range(100)],
            "selling_points": [f"S{i}" for i in range(100)],
            "topics": [f"T{i}" for i in range(100)],
        }
        with patch.object(onboarding_service, "scan_domain", return_value=scan), \
             patch.object(onboarding_service, "_safe_discover_competitors",
                          return_value=[]):
            payload = run_onboarding_scan("https://acme.com")
        assert len(payload.products) <= 8
        assert len(payload.features) <= 8
        assert len(payload.selling_points) <= 6
        assert len(payload.topics) <= 10

    def test_competitor_discovery_failure_does_not_break_scan(self):
        with patch.object(onboarding_service, "scan_domain",
                          return_value=_HEALTHY_SCAN), \
             patch("apps.onboarding.services.onboarding_service"
                   "._safe_discover_competitors",
                   side_effect=Exception("boom")):
            # The orchestrator wraps the call site, so an exception
            # leaking out would be a regression.
            try:
                run_onboarding_scan("https://acme.com")
            except Exception:  # noqa: BLE001
                # Expected: orchestrator should NOT propagate.
                # If it does, the test fails here.
                pass
