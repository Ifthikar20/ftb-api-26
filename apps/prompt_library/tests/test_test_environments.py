"""End-to-end tests for the TestEnvironment REST surface.

Covers: list/create/rename/delete, prompt-membership add/remove,
ownership checks (one user can't see/mutate another's envs), and the
duplicate-name 409 path.
"""
from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.prompt_library.models import BrandPrompt, TestEnvironment
from apps.prompt_library.tests.factories import PromptFactory
from apps.websites.tests.factories import WebsiteFactory


def _list_url(wid):
    return reverse("prompt-library-test-environments", kwargs={"website_id": wid})


def _detail_url(wid, eid):
    return reverse("prompt-library-test-environment-detail",
                   kwargs={"website_id": wid, "env_id": eid})


def _prompts_url(wid, eid):
    return reverse("prompt-library-test-environment-prompts",
                   kwargs={"website_id": wid, "env_id": eid})


class TestEnvironmentCRUDTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.website = WebsiteFactory(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _unwrap(self, resp):
        # The DRF envelope renderer wraps non-paginated responses as
        # {success, data}. Tests speak in terms of the inner payload.
        body = resp.json()
        return body.get("data", body) if isinstance(body, dict) else body

    def test_create_and_list(self):
        resp = self.client.post(_list_url(self.website.id), {"name": "Sprint 12"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = self._unwrap(resp)
        self.assertEqual(data["name"], "Sprint 12")
        self.assertEqual(data["prompt_count"], 0)

        resp = self.client.get(_list_url(self.website.id))
        self.assertEqual(resp.status_code, 200)
        rows = self._unwrap(resp)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Sprint 12")

    def test_duplicate_name_rejected(self):
        self.client.post(_list_url(self.website.id), {"name": "Dup"}, format="json")
        resp = self.client.post(_list_url(self.website.id), {"name": "Dup"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_blank_name_rejected(self):
        resp = self.client.post(_list_url(self.website.id), {"name": "   "}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_create_with_initial_prompts(self):
        bp = BrandPrompt.objects.create(
            website=self.website, prompt=PromptFactory(),
        )
        resp = self.client.post(
            _list_url(self.website.id),
            {"name": "With prompts", "prompt_ids": [str(bp.id)]},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        env = TestEnvironment.objects.get(id=self._unwrap(resp)["id"])
        self.assertEqual(env.prompts.count(), 1)

    def test_rename(self):
        resp = self.client.post(_list_url(self.website.id), {"name": "Old"}, format="json")
        eid = self._unwrap(resp)["id"]
        resp = self.client.patch(_detail_url(self.website.id, eid),
                                 {"name": "New"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._unwrap(resp)["name"], "New")

    def test_rename_to_existing_name_conflicts(self):
        self.client.post(_list_url(self.website.id), {"name": "A"}, format="json")
        resp = self.client.post(_list_url(self.website.id), {"name": "B"}, format="json")
        bid = self._unwrap(resp)["id"]
        resp = self.client.patch(_detail_url(self.website.id, bid),
                                 {"name": "A"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_delete(self):
        resp = self.client.post(_list_url(self.website.id), {"name": "Bye"}, format="json")
        eid = self._unwrap(resp)["id"]
        resp = self.client.delete(_detail_url(self.website.id, eid))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(TestEnvironment.objects.filter(id=eid).exists())


class TestEnvironmentMembershipTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.website = WebsiteFactory(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.bp1 = BrandPrompt.objects.create(website=self.website, prompt=PromptFactory())
        self.bp2 = BrandPrompt.objects.create(website=self.website, prompt=PromptFactory())
        # Belongs to a different website — must never end up in our env
        # even if the FE sends its id, because we filter by website.
        other_website = WebsiteFactory(user=self.user)
        self.bp_other = BrandPrompt.objects.create(
            website=other_website, prompt=PromptFactory(),
        )
        self.env = TestEnvironment.objects.create(
            website=self.website, name="My Env", created_by=self.user,
        )

    def _unwrap(self, resp):
        body = resp.json()
        return body.get("data", body) if isinstance(body, dict) else body

    def test_add_prompts(self):
        resp = self.client.post(
            _prompts_url(self.website.id, self.env.id),
            {"brand_prompt_ids": [str(self.bp1.id), str(self.bp2.id)]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._unwrap(resp)["prompt_count"], 2)

    def test_add_rejects_other_websites_prompt(self):
        resp = self.client.post(
            _prompts_url(self.website.id, self.env.id),
            {"brand_prompt_ids": [str(self.bp_other.id)]},
            format="json",
        )
        # Endpoint returns 200 but the cross-tenant id is silently
        # filtered out — that's the safe behavior.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._unwrap(resp)["prompt_count"], 0)

    def test_remove_prompts(self):
        self.env.prompts.add(self.bp1, self.bp2)
        resp = self.client.delete(
            _prompts_url(self.website.id, self.env.id),
            {"brand_prompt_ids": [str(self.bp1.id)]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._unwrap(resp)["prompt_count"], 1)

    def test_empty_body_rejected(self):
        resp = self.client.post(
            _prompts_url(self.website.id, self.env.id),
            {"brand_prompt_ids": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


class TestEnvironmentOwnershipTests(TestCase):
    """Another user's envs are invisible and unmutable."""

    def setUp(self):
        self.owner = UserFactory()
        self.intruder = UserFactory()
        self.website = WebsiteFactory(user=self.owner)
        self.env = TestEnvironment.objects.create(
            website=self.website, name="Owner Env", created_by=self.owner,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.intruder)

    def test_intruder_cannot_list(self):
        # The intruder doesn't own the website, so get_for_user 404s.
        resp = self.client.get(_list_url(self.website.id))
        self.assertIn(resp.status_code, (403, 404))

    def test_intruder_cannot_rename(self):
        resp = self.client.patch(
            _detail_url(self.website.id, self.env.id),
            {"name": "Stolen"}, format="json",
        )
        self.assertIn(resp.status_code, (403, 404))

    def test_intruder_cannot_delete(self):
        resp = self.client.delete(_detail_url(self.website.id, self.env.id))
        self.assertIn(resp.status_code, (403, 404))
        self.assertTrue(TestEnvironment.objects.filter(id=self.env.id).exists())
