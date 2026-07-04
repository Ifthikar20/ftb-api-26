"""Tests for the Source Intelligence pipeline (scan -> read -> sentiment)."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.citations.models import SourceScan, SourceScanStatus
from apps.citations.services import content_reader, source_scan, web_search
from apps.websites.tests.factories import WebsiteFactory


def _resp(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


SERP_PAYLOAD = {
    "results": [
        {"url": "https://www.reddit.com/r/Dallas/comments/abc/best_bagels/",
         "title": "Where are the best bagels at??", "snippet": "..."},
        {"url": "https://dallasobserver.com/best-bagels", "title": "Ranked", "snippet": "..."},
    ]
}

REDDIT_PAYLOAD = [
    {"data": {"children": [{"data": {
        "title": "Where are the best bagels at??",
        "subreddit": "Dallas", "score": 120, "selftext": "Looking for bagels.",
    }}]}},
    {"data": {"children": [
        {"kind": "t1", "data": {"body": "Starship without question.", "score": 98, "replies": ""}},
        {"kind": "t1", "data": {"body": "Tried. Was not impressed.", "score": 23, "replies": ""}},
        {"kind": "t1", "data": {"body": "[deleted]", "score": 5, "replies": ""}},
    ]}},
]


# -- web_search ---------------------------------------------------------------

@pytest.mark.django_db
def test_search_web_parses_and_ranks(settings):
    settings.PERPLEXITY_API_KEY = "pplx-test"
    with patch.object(web_search.requests, "post", return_value=_resp(SERP_PAYLOAD)) as mock_post:
        results = web_search.search_web("best bagels in dallas")

    assert [r["rank"] for r in results] == [1, 2]
    assert results[0]["domain"] == "reddit.com"
    body = mock_post.call_args.kwargs["json"]
    assert body["query"] == "best bagels in dallas"


@pytest.mark.django_db
def test_search_web_unconfigured_returns_empty(settings):
    settings.PERPLEXITY_API_KEY = ""
    assert web_search.search_web("anything") == []


# -- content_reader -----------------------------------------------------------

def test_reddit_reader_extracts_scored_comments():
    with patch.object(content_reader.requests, "get", return_value=_resp(REDDIT_PAYLOAD)) as mock_get:
        out = content_reader.read_reddit_thread(
            "https://www.reddit.com/r/Dallas/comments/abc/best_bagels/"
        )

    assert out["status"] == "ok"
    assert out["kind"] == "reddit"
    assert "[+98] Starship without question." in out["text"]
    assert "[deleted]" not in out["text"]
    called_url = mock_get.call_args.args[0]
    assert called_url.endswith(".json")


def test_read_url_dispatches_reddit():
    with patch.object(content_reader, "read_reddit_thread", return_value={"status": "ok"}) as mock_reddit:
        content_reader.read_url("https://reddit.com/r/x/comments/1/abc/")
    mock_reddit.assert_called_once()


def test_page_reader_blocked_maps_to_blocked_status():
    with patch.object(
        content_reader, "safe_get",
        side_effect=content_reader.FetchError("HTTP 403 from host"),
    ):
        out = content_reader.read_page("https://www.yelp.com/c/dallas/bagels")
    assert out["status"] == "blocked"


def test_page_reader_extracts_visible_text():
    html = "<html><head><script>x()</script></head><body><h1>Bagels</h1><p>Great list.</p></body></html>"
    fake = MagicMock()
    fake.text = html
    with patch.object(content_reader, "safe_get", return_value=fake):
        out = content_reader.read_page("https://example.com/bagels")
    assert out["status"] == "ok"
    assert "Bagels" in out["text"] and "Great list." in out["text"]
    assert "x()" not in out["text"]


# -- orchestrator ---------------------------------------------------------------

ANALYSIS = {
    "brands": [
        {"name": "Starship Bagel", "mentions": 3, "sentiment": 0.9, "weight": 0.9,
         "quotes": ["Starship without question."]},
        {"name": "Shug's Bagels", "mentions": 1, "sentiment": 0.2, "weight": 0.3, "quotes": []},
    ],
    "target_brand_present": False,
    "summary": "Community strongly favors Starship.",
}


@pytest.mark.django_db
def test_run_scan_full_pipeline(settings):
    settings.PERPLEXITY_API_KEY = "pplx-test"
    website = WebsiteFactory(name="Brooklyn Bagel Co", url="https://brooklynbagel.co")
    scan = SourceScan.objects.create(website=website, query="best bagels in dallas")

    with patch.object(web_search.requests, "post", return_value=_resp(SERP_PAYLOAD)), \
         patch.object(source_scan.content_reader, "read_url",
                      return_value={"status": "ok", "kind": "reddit",
                                    "text": "[+98] Starship without question.",
                                    "word_count": 5, "detail": ""}), \
         patch.object(source_scan.source_sentiment, "analyze_content", return_value=ANALYSIS):
        source_scan.run_scan(scan)

    scan.refresh_from_db()
    assert scan.status == SourceScanStatus.COMPLETE
    assert scan.results_count == 2
    assert scan.analyzed_count == 2
    assert scan.brands[0]["name"] == "Starship Bagel"
    assert scan.brands[0]["sentiment"] == pytest.approx(0.9, abs=0.01)
    # Rank-weighted: present in both results (rank 1 and 2).
    assert scan.brands[0]["results_present_in"] == 2
    assert scan.brands[0]["top_quote"] == "Starship without question."
    assert scan.own_brand_present is False
    first = scan.results.first()
    assert first.source_class == "reddit"
    assert first.fetch_status == "ok"


@pytest.mark.django_db
def test_run_scan_marks_blocked_results_and_continues(settings):
    settings.PERPLEXITY_API_KEY = "pplx-test"
    website = WebsiteFactory()
    scan = SourceScan.objects.create(website=website, query="q")

    def read_url(url):
        if "reddit" in url:
            return {"status": "ok", "kind": "reddit", "text": "content", "word_count": 1, "detail": ""}
        return {"status": "blocked", "kind": "page", "text": "", "word_count": 0, "detail": "403"}

    with patch.object(web_search.requests, "post", return_value=_resp(SERP_PAYLOAD)), \
         patch.object(source_scan.content_reader, "read_url", side_effect=read_url), \
         patch.object(source_scan.source_sentiment, "analyze_content", return_value=ANALYSIS):
        source_scan.run_scan(scan)

    scan.refresh_from_db()
    assert scan.status == SourceScanStatus.COMPLETE
    assert scan.analyzed_count == 1
    blocked = scan.results.get(rank=2)
    assert blocked.fetch_status == "blocked"
    assert blocked.brands == []


@pytest.mark.django_db
def test_run_scan_fails_cleanly_without_results(settings):
    settings.PERPLEXITY_API_KEY = ""
    website = WebsiteFactory()
    scan = SourceScan.objects.create(website=website, query="q")
    source_scan.run_scan(scan)
    scan.refresh_from_db()
    assert scan.status == SourceScanStatus.FAILED
    assert "no search results" in scan.error


@pytest.mark.django_db
def test_own_brand_detection(settings):
    settings.PERPLEXITY_API_KEY = "pplx-test"
    website = WebsiteFactory(name="Starship Bagel", url="https://starshipbagel.com")
    scan = SourceScan.objects.create(website=website, query="best bagels in dallas")

    with patch.object(web_search.requests, "post", return_value=_resp(SERP_PAYLOAD)), \
         patch.object(source_scan.content_reader, "read_url",
                      return_value={"status": "ok", "kind": "reddit", "text": "t",
                                    "word_count": 1, "detail": ""}), \
         patch.object(source_scan.source_sentiment, "analyze_content", return_value=ANALYSIS):
        source_scan.run_scan(scan)

    scan.refresh_from_db()
    assert scan.own_brand_present is True


# -- API ------------------------------------------------------------------------

@pytest.fixture
def auth_client():
    user = UserFactory()
    website = WebsiteFactory(user=user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, website


@pytest.mark.django_db
class TestSourceScanAPI:
    def test_create_dispatches_task(self, auth_client, settings):
        settings.PERPLEXITY_API_KEY = "pplx-test"
        client, user, website = auth_client
        with patch("apps.citations.tasks.run_source_scan.delay") as mock_delay:
            response = client.post(
                f"/api/v1/citations/websites/{website.id}/source-scans/",
                {"query": "best bagels in dallas"},
                format="json",
            )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"
        mock_delay.assert_called_once_with(data["id"])

    def test_create_requires_configuration(self, auth_client, settings):
        settings.PERPLEXITY_API_KEY = ""
        client, user, website = auth_client
        response = client.post(
            f"/api/v1/citations/websites/{website.id}/source-scans/",
            {"query": "q"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_rejects_empty_query(self, auth_client, settings):
        settings.PERPLEXITY_API_KEY = "pplx-test"
        client, user, website = auth_client
        response = client.post(
            f"/api/v1/citations/websites/{website.id}/source-scans/",
            {"query": "  "},
            format="json",
        )
        assert response.status_code == 400

    def test_active_scan_cap(self, auth_client, settings):
        settings.PERPLEXITY_API_KEY = "pplx-test"
        client, user, website = auth_client
        for _ in range(3):
            SourceScan.objects.create(website=website, query="q")
        response = client.post(
            f"/api/v1/citations/websites/{website.id}/source-scans/",
            {"query": "q"},
            format="json",
        )
        assert response.status_code == 429

    def test_list_and_detail(self, auth_client):
        client, user, website = auth_client
        scan = SourceScan.objects.create(
            website=website, query="q", status=SourceScanStatus.COMPLETE,
            brands=[{"name": "Starship Bagel"}],
        )
        listing = client.get(f"/api/v1/citations/websites/{website.id}/source-scans/")
        assert listing.status_code == 200
        assert listing.json()["data"]["scans"][0]["id"] == str(scan.id)

        detail = client.get(
            f"/api/v1/citations/websites/{website.id}/source-scans/{scan.id}/"
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["brands"][0]["name"] == "Starship Bagel"

    def test_cross_tenant_404(self, auth_client):
        client, user, website = auth_client
        other = WebsiteFactory()
        response = client.get(f"/api/v1/citations/websites/{other.id}/source-scans/")
        assert response.status_code == 404


# -- yelp reader ---------------------------------------------------------------

YELP_BIZ = {
    "name": "Starship Bagel", "rating": 4.5, "review_count": 402,
    "price": "$", "categories": [{"title": "Bagels"}],
}
YELP_REVIEWS = {"reviews": [
    {"rating": 5, "text": "Best NY-style bagel in Texas."},
    {"rating": 4, "text": "Great chew, long line."},
]}
YELP_SEARCH = {"businesses": [
    YELP_BIZ,
    {"name": "Shug's Bagels", "rating": 4.4, "review_count": 1002,
     "categories": [{"title": "Bagels"}]},
]}


def _yelp_get_side_effect(responses):
    def fake(url, params=None, headers=None, timeout=None):
        for fragment, payload in responses.items():
            if fragment in url:
                return _resp(payload)
        raise AssertionError(f"unexpected yelp url {url}")
    return fake


@pytest.mark.django_db
def test_yelp_business_page_via_api(settings):
    settings.YELP_API_KEY = "yelp-test"
    fake = _yelp_get_side_effect({
        "/businesses/starship-bagel-lewisville/reviews": YELP_REVIEWS,
        "/businesses/starship-bagel-lewisville": YELP_BIZ,
    })
    with patch.object(content_reader.requests, "get", side_effect=fake):
        out = content_reader.read_yelp("https://www.yelp.com/biz/starship-bagel-lewisville")

    assert out["status"] == "ok"
    assert out["kind"] == "yelp"
    assert "4.5 stars from 402 reviews" in out["text"]
    assert "[5 stars] Best NY-style bagel in Texas." in out["text"]


@pytest.mark.django_db
def test_yelp_category_page_via_search_api(settings):
    settings.YELP_API_KEY = "yelp-test"
    captured = {}

    def fake(url, params=None, headers=None, timeout=None):
        captured.update(params or {})
        return _resp(YELP_SEARCH)

    with patch.object(content_reader.requests, "get", side_effect=fake):
        out = content_reader.read_yelp("https://www.yelp.com/c/dallas/bagels")

    assert out["status"] == "ok"
    assert captured["term"] == "bagels"
    assert captured["location"] == "dallas"
    assert "Starship Bagel: 4.5 stars from 402 reviews" in out["text"]
    assert "Shug's Bagels: 4.4 stars from 1002 reviews" in out["text"]


@pytest.mark.django_db
def test_yelp_search_page_parses_query_params(settings):
    settings.YELP_API_KEY = "yelp-test"
    captured = {}

    def fake(url, params=None, headers=None, timeout=None):
        captured.update(params or {})
        return _resp(YELP_SEARCH)

    with patch.object(content_reader.requests, "get", side_effect=fake):
        out = content_reader.read_yelp(
            "https://www.yelp.com/search?find_desc=Bagels&find_loc=Dallas%2C+TX%2C+USA"
        )

    assert out["status"] == "ok"
    assert captured["term"] == "Bagels"
    assert captured["location"] == "Dallas, TX, USA"


@pytest.mark.django_db
def test_yelp_without_key_stays_blocked(settings):
    settings.YELP_API_KEY = ""
    out = content_reader.read_yelp("https://www.yelp.com/biz/anything")
    assert out["status"] == "blocked"
    assert "YELP_API_KEY" in out["detail"]


@pytest.mark.django_db
def test_read_url_dispatches_yelp(settings):
    settings.YELP_API_KEY = "yelp-test"
    with patch.object(content_reader, "read_yelp", return_value={"status": "ok"}) as mock_yelp:
        content_reader.read_url("https://www.yelp.com/c/dallas/bagels")
    mock_yelp.assert_called_once()
