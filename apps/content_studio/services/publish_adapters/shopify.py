"""Shopify publish adapter (Admin REST blog articles)."""
from __future__ import annotations

from apps.content_studio.services.publish_adapters.base import BasePublishAdapter


class ShopifyAdapter(BasePublishAdapter):
    provider = "shopify"

    def build_payload(self, draft, target) -> dict:
        cfg = target.config or {}
        return {
            "shop": cfg.get("shop", ""),
            "blog_id": cfg.get("blog_id", ""),
            "article": {
                "title": draft.title,
                "body_html": draft.body_html or draft.body_markdown,
                "published": True,
            },
        }

    def _publish_live(self, draft, target) -> dict:
        import requests
        cfg = target.config or {}
        shop = (cfg.get("shop") or "").rstrip("/")
        blog_id = cfg.get("blog_id", "")
        url = f"https://{shop}/admin/api/2024-04/blogs/{blog_id}/articles.json"
        payload = self.build_payload(draft, target)
        headers = {
            "X-Shopify-Access-Token": cfg.get("access_token", ""),
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json={"article": payload["article"]}, headers=headers, timeout=30)
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
        article = data.get("article") or {}
        return {
            "status": "published",
            "external_id": str(article.get("id", "")),
            "external_url": "",
            "request_payload": payload,
            "response_payload": data,
            "error_message": "",
        }
