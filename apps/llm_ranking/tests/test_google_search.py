"""Unit tests for the Google Custom Search JSON API client."""

from unittest.mock import MagicMock, patch

import pytest

from apps.llm_ranking.services import google_search


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


def _stub_response(items):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"items": items})
    return resp


@pytest.mark.django_db
def test_search_returns_empty_when_not_configured(settings):
    settings.GOOGLE_API_KEY = ""
    settings.GOOGLE_CSE_ID = ""
    assert google_search.search("anything") == []


@pytest.mark.django_db
def test_search_parses_publisher_url_and_domain(settings):
    settings.GOOGLE_API_KEY = "k"
    settings.GOOGLE_CSE_ID = "cx"

    items = [
        {
            "link":    "https://www.nytimes.com/2026/01/01/article.html",
            "title":   "Some headline",
            "snippet": "lede here",
        }
    ]
    with patch.object(google_search.requests, "get", return_value=_stub_response(items)) as mock_get:
        out = google_search.search("nyt thing", num=3)

    assert len(out) == 1
    assert out[0]["url"].startswith("https://www.nytimes.com/")
    assert out[0]["domain"] == "nytimes.com"
    assert out[0]["title"] == "Some headline"
    assert out[0]["snippet"] == "lede here"
    # Hit the API with the right CSE params.
    _, kwargs = mock_get.call_args
    params = kwargs["params"]
    assert params["q"] == "nyt thing"
    assert params["num"] == 3
    assert params["key"] == "k"
    assert params["cx"] == "cx"


@pytest.mark.django_db
def test_search_caches_repeat_calls(settings):
    settings.GOOGLE_API_KEY = "k"
    settings.GOOGLE_CSE_ID = "cx"

    with patch.object(
        google_search.requests, "get",
        return_value=_stub_response([{"link": "https://a.com", "title": "A"}]),
    ) as mock_get:
        google_search.search("q1")
        google_search.search("q1")

    assert mock_get.call_count == 1


@pytest.mark.django_db
def test_search_swallows_network_errors(settings):
    settings.GOOGLE_API_KEY = "k"
    settings.GOOGLE_CSE_ID = "cx"
    err = google_search.requests.RequestException("boom")
    with patch.object(google_search.requests, "get", side_effect=err):
        assert google_search.search("q") == []


@pytest.mark.django_db
def test_search_many_dedupes_and_credits_queries(settings):
    settings.GOOGLE_API_KEY = "k"
    settings.GOOGLE_CSE_ID = "cx"

    def fake_get(url, params=None, timeout=None):
        q = params["q"]
        if q == "q1":
            return _stub_response([
                {"link": "https://a.com", "title": "A"},
                {"link": "https://b.com", "title": "B"},
            ])
        return _stub_response([
            {"link": "https://b.com", "title": "B"},
            {"link": "https://c.com", "title": "C"},
        ])

    with patch.object(google_search.requests, "get", side_effect=fake_get):
        out = google_search.search_many(["q1", "q2"], num_per_query=2, max_total=10)

    urls = {r["url"] for r in out}
    assert urls == {"https://a.com", "https://b.com", "https://c.com"}
    by_url = {r["url"]: r for r in out}
    assert by_url["https://b.com"]["queries"] == ["q1", "q2"]
    assert by_url["https://a.com"]["queries"] == ["q1"]
    assert by_url["https://c.com"]["queries"] == ["q2"]


@pytest.mark.django_db
def test_search_many_respects_max_total(settings):
    settings.GOOGLE_API_KEY = "k"
    settings.GOOGLE_CSE_ID = "cx"
    items = [{"link": f"https://x{i}.com", "title": f"X{i}"} for i in range(10)]
    with patch.object(google_search.requests, "get", return_value=_stub_response(items)):
        out = google_search.search_many(["q"], num_per_query=10, max_total=3)
    assert len(out) == 3
