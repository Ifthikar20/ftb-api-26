"""HubSpot CMS Blog Posts publish adapter."""
from __future__ import annotations

from apps.content_studio.services.publish_adapters.base import BasePublishAdapter


class HubSpotAdapter(BasePublishAdapter):
    provider = "hubspot"

    def build_payload(self, draft, target) -> dict:
        cfg = target.config or {}
        return {
            "name": draft.title,
            "postBody": draft.body_html or draft.body_markdown,
            "contentGroupId": cfg.get("content_group_id", ""),
            "state": "PUBLISHED",
        }

    def _publish_live(self, draft, target) -> dict:
        import requests
        cfg = target.config or {}
        url = "https://api.hubapi.com/cms/v3/blogs/posts"
        payload = self.build_payload(draft, target)
        headers = {
            "Authorization": f"Bearer {cfg.get('access_token', '')}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        try:
            data = resp.json()
        except Exception:
            data = {"text": resp.text[:2000]}
        if resp.status_code >= 400:
            return {
                "status": "failed",
                "external_id": "",
                "external_url": "",
                "request_payload": payload,
                "response_payload": data,
                "error_message": f"HTTP {resp.status_code}",
            }
        return {
            "status": "published",
            "external_id": str(data.get("id", "")),
            "external_url": data.get("url", "") or "",
            "request_payload": payload,
            "response_payload": data,
            "error_message": "",
        }
