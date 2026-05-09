"""WordPress publish adapter (REST API + Application Passwords)."""
from __future__ import annotations

from apps.content_studio.services.publish_adapters.base import BasePublishAdapter


class WordPressAdapter(BasePublishAdapter):
    provider = "wordpress"

    def build_payload(self, draft, target) -> dict:
        cfg = target.config or {}
        return {
            "site_url": cfg.get("site_url", ""),
            "endpoint": "/wp-json/wp/v2/posts",
            "title": draft.title,
            "content": draft.body_html or draft.body_markdown,
            "status": "publish",
            "auth_user": cfg.get("user", ""),
        }

    def _publish_live(self, draft, target) -> dict:
        import requests
        cfg = target.config or {}
        site_url = (cfg.get("site_url") or "").rstrip("/")
        url = f"{site_url}/wp-json/wp/v2/posts"
        body = {
            "title": draft.title,
            "content": draft.body_html or draft.body_markdown,
            "status": "publish",
        }
        resp = requests.post(
            url,
            json=body,
            auth=(cfg.get("user", ""), cfg.get("app_password", "")),
            timeout=30,
        )
        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text[:2000]}
        if resp.status_code >= 400:
            return {
                "status": "failed",
                "external_id": "",
                "external_url": "",
                "request_payload": body,
                "response_payload": data,
                "error_message": f"HTTP {resp.status_code}",
            }
        return {
            "status": "published",
            "external_id": str(data.get("id", "")),
            "external_url": data.get("link", "") or "",
            "request_payload": body,
            "response_payload": data,
            "error_message": "",
        }
