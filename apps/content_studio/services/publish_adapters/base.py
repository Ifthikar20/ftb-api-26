"""Base classes for publish adapters."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger("apps")


class BasePublishAdapter(ABC):
    """ABC for a publishing destination.

    Implementations must return a dict with keys::

        status: "published" | "failed" | "queued"
        external_id: str
        external_url: str
        request_payload: dict
        response_payload: dict
        error_message: str (only when failed)

    Real HTTP calls are gated by ``settings.CONTENT_STUDIO_PUBLISH_LIVE``;
    when False (the default in dev) :meth:`dry_run` is invoked instead.
    """

    provider: str = ""

    @abstractmethod
    def build_payload(self, draft, target) -> dict:
        """Return the request payload that would be sent."""

    def dry_run(self, draft, target) -> dict:
        payload = self.build_payload(draft, target)
        return {
            "status": "published",
            "external_id": "dry-run",
            "external_url": "",
            "request_payload": payload,
            "response_payload": {"dry_run": True},
            "error_message": "",
        }

    def publish(self, draft, target) -> dict:
        if not getattr(settings, "CONTENT_STUDIO_PUBLISH_LIVE", False):
            return self.dry_run(draft, target)
        try:
            return self._publish_live(draft, target)
        except Exception as exc:
            logger.exception("publish_live failed (%s): %s", self.provider, exc)
            return {
                "status": "failed",
                "external_id": "",
                "external_url": "",
                "request_payload": self.build_payload(draft, target),
                "response_payload": {},
                "error_message": str(exc),
            }

    def _publish_live(self, draft, target) -> dict:
        # Default: same as dry-run; real adapters override.
        return self.dry_run(draft, target)
