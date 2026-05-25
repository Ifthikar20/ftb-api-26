"""Region routing into provider request bodies (no network)."""


class _Resp:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "hi"}}], "usage": {}}


def test_perplexity_passes_user_location(monkeypatch, settings):
    settings.PERPLEXITY_API_KEY = "test-key"
    import apps.llm_ranking.providers.perplexity as pmod

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json or {})
        return _Resp()

    monkeypatch.setattr(pmod.requests, "post", fake_post)
    result = pmod.PerplexityProvider()._call(
        prompt="best apps to save money", system_prompt="", region="in",
    )
    assert result.succeeded
    assert captured["web_search_options"]["user_location"]["country"] == "IN"


def test_grok_country_when_websearch_enabled(monkeypatch, settings):
    settings.XAI_API_KEY = "test-key"
    settings.LLM_WEBSEARCH_ENABLED = True
    import apps.llm_ranking.providers.grok as gmod

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json or {})
        assert url.startswith("https://api.x.ai/")
        return _Resp()

    monkeypatch.setattr(gmod.requests, "post", fake_post)
    result = gmod.GrokProvider()._call(
        prompt="best apps", system_prompt="", region="ru",
    )
    assert result.succeeded
    sources = captured["search_parameters"]["sources"]
    assert all(s.get("country") == "RU" for s in sources)


def test_grok_no_search_params_when_disabled(monkeypatch, settings):
    settings.XAI_API_KEY = "test-key"
    settings.LLM_WEBSEARCH_ENABLED = False
    import apps.llm_ranking.providers.grok as gmod

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json or {})
        return _Resp()

    monkeypatch.setattr(gmod.requests, "post", fake_post)
    gmod.GrokProvider()._call(prompt="best apps", system_prompt="", region="ru")
    assert "search_parameters" not in captured
