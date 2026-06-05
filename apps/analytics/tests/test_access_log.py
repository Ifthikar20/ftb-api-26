"""Tests for the analytics access-log audit trail."""
from __future__ import annotations

import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from apps.analytics.models import AnalyticsAccessLog
from apps.websites.models import Website


def _user(email="owner@fetchbot.io"):
    from apps.accounts.models import User
    return User.objects.create_user(email=email, password="TestPass123!", full_name="Owner")


def _website(user):
    return Website.objects.create(
        user=user, name="Outfi", url="https://www.outfi.ai",
        pixel_key=uuid.uuid4(), is_active=True,
    )


class AccessLogMiddlewareTest(TestCase):
    def setUp(self):
        self.user = _user()
        self.website = _website(self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_successful_read_is_logged(self):
        resp = self.client.get(f"/api/v1/analytics/{self.website.id}/overview/")
        self.assertEqual(resp.status_code, 200)
        log = AnalyticsAccessLog.objects.filter(website_id_raw=str(self.website.id))
        self.assertEqual(log.count(), 1)
        row = log.first()
        self.assertEqual(row.user_id, self.user.id)
        self.assertEqual(row.user_email, self.user.email)
        self.assertEqual(row.method, "GET")
        self.assertTrue(row.path.endswith("/overview/"))

    def test_denied_cross_tenant_read_is_not_logged_as_access(self):
        # A different user who does not own the website gets 404 and no
        # access row is written (no data was returned to attribute).
        stranger = _user(email="stranger@fetchbot.io")
        c = APIClient()
        c.force_authenticate(user=stranger)
        resp = c.get(f"/api/v1/analytics/{self.website.id}/overview/")
        self.assertIn(resp.status_code, (403, 404))
        self.assertEqual(
            AnalyticsAccessLog.objects.filter(
                website_id_raw=str(self.website.id), user=stranger,
            ).count(),
            0,
        )

    def test_unauthenticated_request_not_logged(self):
        c = APIClient()
        c.get(f"/api/v1/analytics/{self.website.id}/overview/")
        self.assertEqual(AnalyticsAccessLog.objects.count(), 0)

    def test_track_endpoint_not_logged(self):
        # Public pixel ingestion is a write, not an analytics read.
        self.client.post(
            "/api/v1/track/event/",
            {"pixel_key": str(self.website.pixel_key), "url": "https://www.outfi.ai/", "event_type": "pageview"},
            format="json",
        )
        self.assertEqual(AnalyticsAccessLog.objects.count(), 0)


class AccessLogEndpointTest(TestCase):
    def setUp(self):
        self.user = _user()
        self.website = _website(self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_owner_can_read_access_trail(self):
        # Generate two accesses, then read the trail.
        self.client.get(f"/api/v1/analytics/{self.website.id}/overview/")
        self.client.get(f"/api/v1/analytics/{self.website.id}/devices/")
        resp = self.client.get(f"/api/v1/analytics/{self.website.id}/access-log/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertGreaterEqual(body["total"], 2)
        self.assertTrue(all(r["user_email"] == self.user.email for r in body["results"]))

    def test_reading_the_access_log_does_not_log_itself(self):
        before = AnalyticsAccessLog.objects.count()
        self.client.get(f"/api/v1/analytics/{self.website.id}/access-log/")
        after = AnalyticsAccessLog.objects.count()
        self.assertEqual(before, after)

    def test_stranger_cannot_read_access_trail(self):
        stranger = _user(email="stranger@fetchbot.io")
        c = APIClient()
        c.force_authenticate(user=stranger)
        resp = c.get(f"/api/v1/analytics/{self.website.id}/access-log/")
        self.assertIn(resp.status_code, (403, 404))
