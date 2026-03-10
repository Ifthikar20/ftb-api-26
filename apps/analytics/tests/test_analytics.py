"""
Comprehensive test suite for FetchBot Analytics.
Tests: event ingestion, daily stats, funnels, retention, flows, AI insights,
keyword intelligence, and API endpoints.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.analytics.models import (
    Visitor, Session, PageEvent, CustomFunnel,
    TrackedKeyword, KeywordRankHistory,
)
from apps.websites.models import Website


def create_test_user():
    """Create a test user for API tests."""
    from apps.accounts.models import User
    return User.objects.create_user(
        email="test@fetchbot.io",
        password="TestPass123!",
        full_name="Test User",
    )


def create_test_website(user, name="Outfi", url="https://www.outfi.ai"):
    """Create a test website."""
    website = Website.objects.create(
        user=user,
        name=name,
        url=url,
        industry="Fashion",
        pixel_key=uuid.uuid4(),
        is_active=True,
    )
    return website


def seed_analytics_data(website, days=30, visitors_per_day=3):
    """Seed realistic analytics data for tests."""
    now = timezone.now()
    visitors = []
    sessions = []
    events = []

    for d in range(days):
        ts = now - timedelta(days=d)
        for v in range(visitors_per_day):
            visitor, _ = Visitor.objects.get_or_create(
                website=website,
                fingerprint_hash=f"hash_{d}_{v}",
                defaults={
                    "geo_country": "US",
                    "geo_city": "New York",
                    "device_type": ["desktop", "mobile", "tablet"][v % 3],
                    "browser": "Chrome",
                    "os": "MacOS",
                },
            )
            visitors.append(visitor)

            session = Session.objects.create(
                visitor=visitor,
                started_at=ts,
                ended_at=ts + timedelta(minutes=5),
                page_count=3,
                entry_page=f"https://www.outfi.ai/page-{v}",
                exit_page=f"https://www.outfi.ai/exit-{v}",
                source=["google", "direct", "facebook"][v % 3],
                medium=["organic", "", "social"][v % 3],
            )
            sessions.append(session)

            for page_num in range(3):
                PageEvent.objects.create(
                    visitor=visitor,
                    website=website,
                    session=session,
                    url=f"https://www.outfi.ai/page-{page_num}",
                    event_type="pageview",
                    timestamp=ts + timedelta(minutes=page_num),
                )

            # Add a click event
            PageEvent.objects.create(
                visitor=visitor,
                website=website,
                session=session,
                url=f"https://www.outfi.ai/page-0",
                event_type="click",
                timestamp=ts + timedelta(minutes=1, seconds=30),
                properties={"x": 100, "y": 200},
            )

    return visitors, sessions


# ═══════════════════════════════════════════
# Event Ingestion Tests
# ═══════════════════════════════════════════

class EventIngestionServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)

    def test_ingest_pageview_creates_visitor_and_session(self):
        from apps.analytics.services.event_ingestion_service import EventIngestionService

        event = EventIngestionService.ingest_event(
            pixel_key=str(self.website.pixel_key),
            event_data={
                "fingerprint": "unique-browser-fp-001",
                "url": "https://www.outfi.ai/shop",
                "event_type": "pageview",
                "referrer": "https://www.google.com/search?q=outfi",
            },
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "pageview")
        self.assertEqual(event.url, "https://www.outfi.ai/shop")

        # Visitor should be created
        self.assertEqual(Visitor.objects.filter(website=self.website).count(), 1)

        # Session should be auto-created
        self.assertEqual(Session.objects.filter(visitor=event.visitor).count(), 1)
        session = Session.objects.first()
        self.assertEqual(session.source, "google")
        self.assertEqual(session.medium, "organic")

    def test_ingest_with_utm_params(self):
        from apps.analytics.services.event_ingestion_service import EventIngestionService

        EventIngestionService.ingest_event(
            pixel_key=str(self.website.pixel_key),
            event_data={
                "fingerprint": "utm-test-fp",
                "url": "https://www.outfi.ai/?utm_source=newsletter&utm_medium=email&utm_campaign=spring_sale",
                "event_type": "pageview",
            },
        )

        session = Session.objects.first()
        self.assertEqual(session.source, "newsletter")
        self.assertEqual(session.medium, "email")
        self.assertEqual(session.campaign, "spring_sale")

    def test_ingest_invalid_pixel_key_raises(self):
        from apps.analytics.services.event_ingestion_service import EventIngestionService

        with self.assertRaises(Exception):  # ValueError or Django ValidationError
            EventIngestionService.ingest_event(
                pixel_key="invalid-key",
                event_data={"fingerprint": "x", "url": "/", "event_type": "pageview"},
            )

    def test_ingest_batch(self):
        from apps.analytics.services.event_ingestion_service import EventIngestionService

        events = [
            {"fingerprint": f"batch-{i}", "url": f"https://www.outfi.ai/p{i}", "event_type": "pageview"}
            for i in range(5)
        ]
        results = EventIngestionService.ingest_batch(
            pixel_key=str(self.website.pixel_key), events=events
        )
        self.assertEqual(len(results), 5)
        self.assertEqual(PageEvent.objects.filter(website=self.website).count(), 5)

    def test_session_reuse_within_30_min(self):
        from apps.analytics.services.event_ingestion_service import EventIngestionService

        # First event
        e1 = EventIngestionService.ingest_event(
            pixel_key=str(self.website.pixel_key),
            event_data={"fingerprint": "reuse-fp", "url": "https://www.outfi.ai/a", "event_type": "pageview"},
        )
        # Second event within 30 min
        e2 = EventIngestionService.ingest_event(
            pixel_key=str(self.website.pixel_key),
            event_data={"fingerprint": "reuse-fp", "url": "https://www.outfi.ai/b", "event_type": "pageview"},
        )
        # Should reuse same session
        self.assertEqual(e1.session_id, e2.session_id)


# ═══════════════════════════════════════════
# Daily Stats Tests
# ═══════════════════════════════════════════

class DailyStatsServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        seed_analytics_data(self.website, days=10, visitors_per_day=2)

    def test_get_chart_data(self):
        from apps.analytics.services.daily_stats import DailyStatsService
        data = DailyStatsService.get_chart_data(website_id=str(self.website.id), period="30d")
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        self.assertIn("date", data[0])
        self.assertIn("visitors", data[0])
        self.assertIn("pageviews", data[0])

    def test_get_device_breakdown(self):
        from apps.analytics.services.daily_stats import DailyStatsService
        data = DailyStatsService.get_device_breakdown(website_id=str(self.website.id))
        self.assertIsInstance(data, list)
        device_names = [d["name"] for d in data]
        self.assertTrue(any(name in device_names for name in ["Desktop", "Mobile", "Tablet"]))

    def test_get_country_breakdown(self):
        from apps.analytics.services.daily_stats import DailyStatsService
        data = DailyStatsService.get_country_breakdown(website_id=str(self.website.id))
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("name", data[0])
            self.assertIn("visitors", data[0])

    def test_get_bounce_rate(self):
        from apps.analytics.services.daily_stats import DailyStatsService
        rate = DailyStatsService.get_bounce_rate(website_id=str(self.website.id))
        self.assertIsInstance(rate, float)
        self.assertTrue(0 <= rate <= 100)

    def test_get_avg_session_duration(self):
        from apps.analytics.services.daily_stats import DailyStatsService
        duration = DailyStatsService.get_avg_session_duration(website_id=str(self.website.id))
        self.assertIsInstance(duration, str)
        self.assertIn(":", duration)


# ═══════════════════════════════════════════
# Funnel Tests
# ═══════════════════════════════════════════

class FunnelServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        seed_analytics_data(self.website, days=7, visitors_per_day=3)

    def test_create_funnel(self):
        from apps.analytics.services.funnel_service import FunnelService
        funnel = FunnelService.create_funnel(
            website_id=str(self.website.id),
            name="Outfi Purchase Flow",
            steps=[
                {"name": "Landing", "type": "url", "value": "page-0"},
                {"name": "Product", "type": "url", "value": "page-1"},
                {"name": "Checkout", "type": "url", "value": "page-2"},
            ],
            user=self.user,
        )
        self.assertEqual(funnel["name"], "Outfi Purchase Flow")
        self.assertEqual(CustomFunnel.objects.count(), 1)

    def test_calculate_funnel(self):
        from apps.analytics.services.funnel_service import FunnelService
        # Create funnel
        f = FunnelService.create_funnel(
            website_id=str(self.website.id),
            name="Test Funnel",
            steps=[
                {"name": "Page 0", "type": "url", "value": "page-0"},
                {"name": "Page 1", "type": "url", "value": "page-1"},
            ],
        )
        # Calculate
        result = FunnelService.calculate_funnel(
            website_id=str(self.website.id), funnel_id=f["id"]
        )
        self.assertIn("steps", result)
        self.assertEqual(len(result["steps"]), 2)
        self.assertIn("overall_conversion_pct", result)
        # First step should have visitors
        self.assertGreater(result["steps"][0]["visitors"], 0)

    def test_list_funnels(self):
        from apps.analytics.services.funnel_service import FunnelService
        FunnelService.create_funnel(
            website_id=str(self.website.id), name="F1", steps=[{"name": "A", "type": "url", "value": "/a"}, {"name": "B", "type": "url", "value": "/b"}]
        )
        funnels = FunnelService.list_funnels(website_id=str(self.website.id))
        self.assertEqual(len(funnels), 1)


# ═══════════════════════════════════════════
# Retention Tests
# ═══════════════════════════════════════════

class RetentionServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        seed_analytics_data(self.website, days=14, visitors_per_day=2)

    def test_retention_matrix(self):
        from apps.analytics.services.retention_service import RetentionService
        matrix = RetentionService.get_retention_matrix(
            website_id=str(self.website.id), num_weeks=4
        )
        self.assertIn("rows", matrix)
        self.assertIn("num_weeks", matrix)
        if matrix["rows"]:
            row = matrix["rows"][0]
            self.assertIn("cohort", row)
            self.assertIn("cohort_size", row)
            self.assertIn("weeks", row)
            # Week 0 retention should be 100%
            self.assertEqual(row["weeks"][0]["pct"], 100.0)

    def test_retention_curve(self):
        from apps.analytics.services.retention_service import RetentionService
        curve = RetentionService.get_retention_curve(
            website_id=str(self.website.id), num_weeks=4
        )
        self.assertIsInstance(curve, list)
        if curve:
            self.assertIn("week", curve[0])
            self.assertIn("avg_retention_pct", curve[0])


# ═══════════════════════════════════════════
# Flow Tests
# ═══════════════════════════════════════════

class FlowServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        seed_analytics_data(self.website, days=7, visitors_per_day=3)

    def test_user_flows(self):
        from apps.analytics.services.flow_service import FlowService
        flows = FlowService.get_user_flows(website_id=str(self.website.id))
        self.assertIn("nodes", flows)
        self.assertIn("links", flows)
        self.assertIn("total_paths", flows)
        # Should have page-to-page transitions
        if flows["links"]:
            self.assertIn("source", flows["links"][0])
            self.assertIn("target", flows["links"][0])
            self.assertIn("value", flows["links"][0])

    def test_entry_pages(self):
        from apps.analytics.services.flow_service import FlowService
        entry = FlowService.get_entry_pages(website_id=str(self.website.id))
        self.assertIsInstance(entry, list)
        if entry:
            self.assertIn("page", entry[0])
            self.assertIn("count", entry[0])

    def test_exit_pages(self):
        from apps.analytics.services.flow_service import FlowService
        exit_ = FlowService.get_exit_pages(website_id=str(self.website.id))
        self.assertIsInstance(exit_, list)


# ═══════════════════════════════════════════
# AI Insights Tests
# ═══════════════════════════════════════════

class AIInsightsServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        seed_analytics_data(self.website, days=10, visitors_per_day=3)

    def test_generate_insights(self):
        from apps.analytics.services.ai_insights_service import AIInsightsService
        insights = AIInsightsService.generate_insights(website_id=str(self.website.id))
        self.assertIsInstance(insights, list)
        if insights:
            self.assertIn("type", insights[0])
            self.assertIn("title", insights[0])
            self.assertIn("description", insights[0])
            self.assertIn(insights[0]["type"], ["critical", "warning", "opportunity", "info"])

    def test_detect_anomalies(self):
        from apps.analytics.services.ai_insights_service import AIInsightsService
        anomalies = AIInsightsService.detect_anomalies(website_id=str(self.website.id))
        self.assertIsInstance(anomalies, list)

    def test_suggest_actions(self):
        from apps.analytics.services.ai_insights_service import AIInsightsService
        actions = AIInsightsService.suggest_actions(website_id=str(self.website.id))
        self.assertIsInstance(actions, list)
        if actions:
            self.assertIn("action", actions[0])
            self.assertIn("priority", actions[0])


# ═══════════════════════════════════════════
# Keyword Intelligence Tests
# ═══════════════════════════════════════════

class KeywordIntelligenceServiceTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        # Create tracked keywords for outfi.ai
        TrackedKeyword.objects.create(
            website=self.website, keyword="modest fashion",
            current_rank=8, search_volume=5400, difficulty=45,
        )
        TrackedKeyword.objects.create(
            website=self.website, keyword="outfi clothing",
            current_rank=15, search_volume=1200, difficulty=25,
        )
        TrackedKeyword.objects.create(
            website=self.website, keyword="online fashion store",
            current_rank=42, search_volume=22000, difficulty=78,
        )

    def test_score_keyword_page1(self):
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        score = KeywordIntelligenceService.score_keyword(
            keyword="modest fashion", current_rank=8, search_volume=5400, difficulty=45,
        )
        self.assertIn("score", score)
        self.assertIn("grade", score)
        self.assertIn("breakdown", score)
        self.assertIn("recommendation", score)
        self.assertIn("calculation_method", score)
        self.assertGreater(score["score"], 40)  # Page 1 + decent volume = good score

    def test_score_keyword_quick_win(self):
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        score = KeywordIntelligenceService.score_keyword(
            keyword="outfi clothing", current_rank=15, search_volume=1200, difficulty=25,
        )
        # Rank 11-20 + low difficulty = high quick-win score
        self.assertGreater(score["score"], 50)
        self.assertIn("Quick Win", score["recommendation"])

    def test_score_keyword_hard(self):
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        score = KeywordIntelligenceService.score_keyword(
            keyword="online fashion store", current_rank=42, search_volume=22000, difficulty=78,
        )
        self.assertIn("Competitive", score["recommendation"])

    def test_score_keywords_bulk(self):
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        scored = KeywordIntelligenceService.score_keywords_bulk(website_id=str(self.website.id))
        self.assertEqual(len(scored), 3)
        # Should be sorted by score descending
        self.assertGreaterEqual(scored[0]["ai_score"], scored[1]["ai_score"])

    def test_score_grade_labels(self):
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        # Top 3 rank + high volume + low difficulty
        s = KeywordIntelligenceService.score_keyword(keyword="x", current_rank=3, search_volume=10000, difficulty=10)
        self.assertIn(s["grade"]["label"], ["Excellent", "Good"])  # Depends on exact multiplier math
        self.assertGreater(s["score"], 50)

    def test_trending_fallback(self):
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        data = KeywordIntelligenceService.get_trending_keywords()
        self.assertIn("region", data)
        self.assertIn("source", data)


# ═══════════════════════════════════════════
# API Endpoint Tests
# ═══════════════════════════════════════════

class AnalyticsAPITest(APITestCase):
    def setUp(self):
        self.user = create_test_user()
        self.website = create_test_website(self.user)
        seed_analytics_data(self.website, days=7, visitors_per_day=2)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.wid = str(self.website.id)

    def test_chart_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/chart/?period=7d")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_devices_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/devices/")
        self.assertEqual(response.status_code, 200)

    def test_countries_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/countries/")
        self.assertEqual(response.status_code, 200)

    def test_funnels_crud(self):
        # Create
        response = self.client.post(f"/api/v1/analytics/{self.wid}/funnels/", {
            "name": "Outfi Signup",
            "steps": [
                {"name": "Home", "type": "url", "value": "/"},
                {"name": "Pricing", "type": "url", "value": "/pricing"},
            ],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        fid = response.data["id"]

        # List
        response = self.client.get(f"/api/v1/analytics/{self.wid}/funnels/")
        self.assertEqual(response.status_code, 200)

    def test_retention_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/retention/?weeks=4")
        self.assertEqual(response.status_code, 200)
        self.assertIn("rows", response.data)

    def test_flows_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/flows/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("nodes", response.data)

    def test_entry_exit_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/entry-exit/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("entry_pages", response.data)

    def test_visitors_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/visitors/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)

    def test_insights_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/insights/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("insights", response.data)
        self.assertIn("actions", response.data)

    def test_live_events_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/live/")
        self.assertEqual(response.status_code, 200)

    def test_keyword_scores_endpoint(self):
        TrackedKeyword.objects.create(
            website=self.website, keyword="outfi fashion", current_rank=12,
            search_volume=800, difficulty=30,
        )
        response = self.client.get(f"/api/v1/analytics/{self.wid}/keywords/scores/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("keywords", response.data)
        self.assertIn("explanation", response.data)

    def test_keyword_trending_endpoint(self):
        response = self.client.get(f"/api/v1/analytics/{self.wid}/keywords/trending/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("region", response.data)

    def test_unauthenticated_blocked(self):
        """Ensure unauthenticated requests are rejected."""
        client = APIClient()  # No auth
        response = client.get(f"/api/v1/analytics/{self.wid}/chart/")
        self.assertIn(response.status_code, [401, 403])


# ═══════════════════════════════════════════
# Website Creation Tests
# ═══════════════════════════════════════════

class WebsiteCreationTest(APITestCase):
    def setUp(self):
        self.user = create_test_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_website(self):
        response = self.client.post("/api/v1/websites/", {
            "name": "Outfi Store",
            "url": "https://www.outfi.ai",
            "industry": "Fashion",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Outfi Store")
        self.assertIn("pixel_key", response.data)

    def test_create_multiple_websites(self):
        """Project limits are disabled for testing — should allow multiple."""
        for i in range(5):
            response = self.client.post("/api/v1/websites/", {
                "name": f"Site {i}",
                "url": f"https://site{i}.com",
            })
            self.assertEqual(response.status_code, 201)
        self.assertEqual(Website.objects.filter(user=self.user).count(), 5)

    def test_create_website_invalid_url(self):
        response = self.client.post("/api/v1/websites/", {
            "name": "Bad Site",
            "url": "not-a-url",
        })
        self.assertIn(response.status_code, [400, 422])
