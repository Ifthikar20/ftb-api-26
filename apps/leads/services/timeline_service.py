"""
Lead activity timeline service — unified chronological feed.

Aggregates page events, notes, emails, and campaign interactions
into a single sorted stream for the CRM detail view.
"""
import logging

logger = logging.getLogger("apps")


class TimelineService:
    @staticmethod
    def get_timeline(*, lead, limit: int = 50, offset: int = 0) -> dict:
        """
        Build a chronological timeline of all activity for a lead.

        Sources:
          1. PageEvent (visitor behavior)
          2. LeadNote (team member notes)
          3. LeadEmail (outbound emails)

        Returns:
            {"items": [...], "total": int}
        """
        from apps.analytics.models import PageEvent
        from apps.leads.models import LeadEmail, LeadNote

        items = []

        # 1. Page events from the visitor
        if lead.visitor_id:
            events = PageEvent.objects.filter(visitor_id=lead.visitor_id).order_by(
                "-timestamp"
            )[:100]
            for event in events:
                items.append({
                    "type": "page_event",
                    "subtype": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "title": _event_title(event),
                    "details": {
                        "url": event.url,
                        "event_type": event.event_type,
                        "scroll_depth": event.scroll_depth,
                        "time_on_page_ms": event.time_on_page_ms,
                    },
                })

        # 2. Notes
        notes = LeadNote.objects.filter(lead=lead).select_related("author").order_by(
            "-created_at"
        )
        for note in notes:
            items.append({
                "type": "note",
                "subtype": "note",
                "timestamp": note.created_at.isoformat(),
                "title": f"Note by {_author_name(note.author)}",
                "details": {
                    "content": note.content,
                    "author": _author_name(note.author),
                },
            })

        # 3. Emails sent
        emails = LeadEmail.objects.filter(lead=lead).select_related("sent_by").order_by(
            "-sent_at"
        )
        for email in emails:
            items.append({
                "type": "email",
                "subtype": email.status,
                "timestamp": email.sent_at.isoformat(),
                "title": f"Email: {email.subject[:80]}",
                "details": {
                    "subject": email.subject,
                    "to_email": email.to_email,
                    "status": email.status,
                    "sent_by": _author_name(email.sent_by),
                },
            })

        # Email-campaign interactions removed with the campaign feature.

        # Sort all items by timestamp descending
        items.sort(key=lambda x: x["timestamp"], reverse=True)

        total = len(items)
        paginated = items[offset: offset + limit]

        return {"items": paginated, "total": total}


def _event_title(event) -> str:
    """Human-readable title for a page event."""
    labels = {
        "pageview": "Viewed page",
        "form_submit": "Submitted form",
        "click": "Clicked",
        "scroll": "Scrolled",
        "session_end": "Session ended",
        "custom": "Custom event",
    }
    prefix = labels.get(event.event_type, event.event_type)
    # Show a short path instead of the full URL
    path = event.url.split("//", 1)[-1].split("/", 1)[-1] if "//" in event.url else event.url
    return f"{prefix}: /{path[:80]}"


def _author_name(user) -> str:
    """Safely get a display name from a user."""
    if user is None:
        return "System"
    name = getattr(user, "full_name", "") or ""
    if name:
        return name
    return getattr(user, "email", "Unknown")
