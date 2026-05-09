"""Publish adapters dispatch table."""
from __future__ import annotations

from apps.content_studio.services.publish_adapters.base import BasePublishAdapter
from apps.content_studio.services.publish_adapters.export import ManualExportAdapter
from apps.content_studio.services.publish_adapters.hubspot import HubSpotAdapter
from apps.content_studio.services.publish_adapters.shopify import ShopifyAdapter
from apps.content_studio.services.publish_adapters.webflow import WebflowAdapter
from apps.content_studio.services.publish_adapters.wordpress import WordPressAdapter

ADAPTERS: dict[str, type[BasePublishAdapter]] = {
    "wordpress": WordPressAdapter,
    "webflow": WebflowAdapter,
    "shopify": ShopifyAdapter,
    "hubspot": HubSpotAdapter,
    "manual": ManualExportAdapter,
}


def get_adapter(provider: str) -> BasePublishAdapter:
    cls = ADAPTERS.get(provider)
    if cls is None:
        raise ValueError(f"Unknown publish provider: {provider}")
    return cls()


__all__ = [
    "BasePublishAdapter",
    "ADAPTERS",
    "get_adapter",
    "ManualExportAdapter",
    "HubSpotAdapter",
    "ShopifyAdapter",
    "WebflowAdapter",
    "WordPressAdapter",
]
