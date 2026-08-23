"""Brand Security notification producer.

Turns a scan's newly created SafetyAlerts into one in-app notification
when anything high-severity surfaced. Batched deliberately: one bad
audit can raise a dozen findings, and a dozen pushes teaches the user to
ignore all of them. The dashboard Recent Activity feed colors this via
the ``brand_security_alert`` entry in the websites view color map.

Producer-only and guarded like geo_events: a notification failure never
breaks the scan that raised the alerts.
"""
from __future__ import annotations

import logging

from apps.notifications.services.notification_service import NotificationService

logger = logging.getLogger("apps")


def record_security_alerts(website, alerts) -> None:
    """Emit one batched notification for a scan's new high-severity alerts.

    ``alerts`` is the list of SafetyAlert rows the scan just created (any
    severity — filtering happens here so callers stay simple).
    """
    try:
        high = [a for a in alerts if a is not None and a.severity == "high"]
        if not high:
            return
        user = getattr(website, "user", None)
        if user is None:
            return

        detectors = sorted({
            (a.detector_code or a.issue or "finding") for a in high
        })
        count = len(high)
        plural = "s" if count != 1 else ""
        name = website.name or website.url or "your brand"
        NotificationService.create(
            user=user,
            notification_type="brand_security_alert",
            title=f"Brand security: {count} high-severity finding{plural}",
            message=(
                f"AI answers about {name} triggered {count} high-severity "
                f"finding{plural} ({', '.join(detectors)}). Review the "
                f"flagged responses on the Brand Security page."
            ),
            data={
                "website_id": str(website.id),
                "alert_ids": [str(a.id) for a in high],
                "references": [a.reference for a in high],
                "detector_codes": detectors,
            },
            action_url=f"/llm-ranking/{website.id}/brand-security",
        )
    except Exception as exc:  # never let notifications break a scan
        logger.warning(
            "brand security notification failed for website %s: %s",
            getattr(website, "id", "?"), exc,
        )
