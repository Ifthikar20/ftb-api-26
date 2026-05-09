"""Manual export adapter — serializes a draft for download."""
from __future__ import annotations

import json

from apps.content_studio.services.publish_adapters.base import BasePublishAdapter


class ManualExportAdapter(BasePublishAdapter):
    provider = "manual"

    def build_payload(self, draft, target) -> dict:
        return serialize_draft(draft, fmt="json")

    def _publish_live(self, draft, target) -> dict:
        # Manual export never hits an external service; behave like a dry-run.
        return self.dry_run(draft, target)


def serialize_draft(draft, fmt: str = "md") -> dict:
    """Return ``{"filename", "content_type", "body"}`` for a download response."""
    fmt = (fmt or "md").lower()
    safe_title = (draft.title or "draft").replace("/", "-")[:60] or "draft"
    if fmt == "json":
        body = json.dumps({
            "id": str(draft.id),
            "title": draft.title,
            "body_markdown": draft.body_markdown,
            "body_html": draft.body_html,
            "json_ld": draft.json_ld,
            "voice_score": draft.voice_score,
            "accuracy_score": draft.accuracy_score,
        }, indent=2)
        return {"filename": f"{safe_title}.json", "content_type": "application/json", "body": body}
    if fmt == "html":
        body = draft.body_html or f"<article>{draft.body_markdown}</article>"
        return {"filename": f"{safe_title}.html", "content_type": "text/html", "body": body}
    return {
        "filename": f"{safe_title}.md",
        "content_type": "text/markdown",
        "body": draft.body_markdown or "",
    }
