"""Tests for AgentContextDocument CRUD + upload endpoints."""

from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.voice_agent.models import AgentConfig, AgentContextDocument
from apps.websites.models import Website


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        email="owner@acme.test", password="pw12345!"
    )


@pytest.fixture
def other_user(db, django_user_model):
    return django_user_model.objects.create_user(
        email="rival@other.test", password="pw12345!"
    )


@pytest.fixture
def website(db, user):
    site = Website.objects.create(name="Acme", url="https://acme.test", user=user)
    return site


@pytest.fixture
def config(db, website):
    return AgentConfig.objects.create(
        website=website,
        retell_agent_id="agent_test_123",
        is_active=True,
        business_hours={},
    )


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _list_url(website_id):
    return f"/api/v1/voice-agent/{website_id}/context-docs/"


def _upload_url(website_id):
    return f"/api/v1/voice-agent/{website_id}/context-docs/upload/"


def _detail_url(website_id, doc_id):
    return f"/api/v1/voice-agent/{website_id}/context-docs/{doc_id}/"


@patch("apps.voice_agent.api.v1.views._sync_prompt_to_retell", return_value="ok")
def test_create_doc_triggers_sync(mock_sync, client, website, config):
    res = client.post(
        _list_url(website.id),
        {"title": "Hours", "content": "9-5", "is_active": True},
        format="json",
    )
    assert res.status_code == 201
    assert res.data["retell_sync"] == "ok"
    assert AgentContextDocument.objects.filter(website=website).count() == 1
    mock_sync.assert_called_once()


@patch("apps.voice_agent.api.v1.views._sync_prompt_to_retell", return_value="ok")
def test_update_doc_triggers_sync(mock_sync, client, website, config):
    doc = AgentContextDocument.objects.create(
        website=website, title="Hours", content="9-5"
    )
    res = client.put(
        _detail_url(website.id, doc.id),
        {"content": "9-6"},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["retell_sync"] == "ok"
    doc.refresh_from_db()
    assert doc.content == "9-6"
    mock_sync.assert_called_once()


@patch("apps.voice_agent.api.v1.views._sync_prompt_to_retell", return_value="ok")
def test_delete_doc_triggers_sync(mock_sync, client, website, config):
    doc = AgentContextDocument.objects.create(
        website=website, title="Hours", content="9-5"
    )
    res = client.delete(_detail_url(website.id, doc.id))
    assert res.status_code == 204
    assert not AgentContextDocument.objects.filter(id=doc.id).exists()
    mock_sync.assert_called_once()


@patch("apps.voice_agent.api.v1.views._sync_prompt_to_retell", return_value="ok")
def test_upload_md_file(mock_sync, client, website, config):
    upload = SimpleUploadedFile(
        "staff_availability.md",
        b"# Staff Availability\n- Dr. Smith: Mon/Wed/Fri\n",
        content_type="text/markdown",
    )
    res = client.post(_upload_url(website.id), {"file": upload}, format="multipart")
    assert res.status_code == 201
    assert res.data["retell_sync"] == "ok"
    assert "Staff Availability" in res.data["content"]
    # Title derived from filename if not provided
    assert "staff availability" in res.data["title"].lower()


def test_upload_rejects_non_markdown(client, website, config):
    upload = SimpleUploadedFile("evil.exe", b"binary", content_type="application/octet-stream")
    res = client.post(_upload_url(website.id), {"file": upload}, format="multipart")
    assert res.status_code == 400


def test_upload_rejects_too_large(client, website, config):
    big = SimpleUploadedFile("big.md", b"x" * (200 * 1024), content_type="text/markdown")
    res = client.post(_upload_url(website.id), {"file": big}, format="multipart")
    assert res.status_code == 400


@patch("apps.voice_agent.api.v1.views._sync_prompt_to_retell", return_value="failed")
def test_create_surfaces_sync_failure(mock_sync, client, website, config):
    res = client.post(
        _list_url(website.id),
        {"title": "Hours", "content": "9-5", "is_active": True},
        format="json",
    )
    assert res.status_code == 201
    assert res.data["retell_sync"] == "failed"
    # DB write still succeeded
    assert AgentContextDocument.objects.filter(website=website).count() == 1
