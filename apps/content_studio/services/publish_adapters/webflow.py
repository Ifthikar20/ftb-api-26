"""Webflow publish adapter (CMS Data API)."""
from __future__ import annotations

from apps.content_studio.services.publish_adapters.base import BasePublishAdapter


class WebflowAdapter(BasePublishAdapter):
    provider = "webflow"

    def build_payload(self, draft, target) -> dict:
        cfg = target.config or {}
        return {
            "site_id": cfg.get("site_id", ""),
            "collection_id": cfg.get("collection_id", ""),
            "fields": {
                "name": draft.title,
                "slug": _slugify(draft.title),
                "post-body": draft.body_html or draft.body_markdown,
                "_archived": False,
                "_draft": False,
            },
        }

    def _publish_live(self, draft, target) -> dict:
        import requests
        cfg = target.config or {}
        url = f"https://api.webflow.com/v2/collections/{cfg.get('collection_id', '')}/items/live"
        payload = self.build_payload(draft, target)
        headers = {
            "Authorization": f"Bearer {cfg.get('api_token', '')}",
            "accept": "application/json",
            "content-type": "application/json",
        }
        resp = requests.post(url, json={"fieldData": payload["fields"]}, headers=headers, timeout=30)
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
            "external_id": str(data.get("id", "") or data.get("_id", "")),
            "external_url": "",
            "request_payload": payload,
            "response_payload": data,
            "error_message": "",
        }


def _slugify(text: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:120] or "post"
