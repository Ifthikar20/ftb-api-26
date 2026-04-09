"""Tool-call handlers shared by the Retell webhook view and the LiveKit agent worker.

Each function takes the website id, parsed arguments, and an optional external call
identifier (used for linking the resulting record back to a CallLog). They return a
plain dict ``{"result": str}`` so callers can wrap the result in a DRF Response or
return it directly to a LiveKit function-tool callback.

This module contains *no* DRF imports so it is safe to import from a non-Django
LiveKit worker process that has been bootstrapped with django.setup().
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone as tz
from django.utils.dateparse import parse_date, parse_datetime

from apps.voice_agent.models import AgentConfig, CallLog
from apps.voice_agent.services.calendar_service import CalendarService
from apps.voice_agent.services.call_service import CallService

logger = logging.getLogger(__name__)


def _find_call_log(external_call_id: str) -> CallLog | None:
    if not external_call_id:
        return None
    return CallLog.objects.filter(external_call_id=external_call_id).first()


def schedule_appointment(
    website_id: str, args: dict[str, Any], external_call_id: str = ""
) -> dict[str, str]:
    """Book an appointment from a tool call."""
    date = parse_date(args.get("preferred_date", ""))
    time_str = args.get("preferred_time", "")

    if not date or not time_str:
        return {"result": "I need both a date and time to schedule. Could you provide those?"}

    try:
        hour, minute = map(int, time_str.split(":"))
    except (ValueError, AttributeError):
        return {"result": "I couldn't understand the time. Please use HH:MM format."}

    start_time = tz.make_aware(
        datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
    )

    call_log = _find_call_log(external_call_id)
    duration = (
        AgentConfig.objects.filter(website_id=website_id)
        .values_list("appointment_duration_minutes", flat=True)
        .first()
        or 30
    )

    try:
        event = CalendarService.book_appointment(
            website_id=website_id,
            attendee_name=args.get("attendee_name", ""),
            attendee_phone=args.get("attendee_phone", ""),
            attendee_email=args.get("attendee_email", ""),
            start_time=start_time,
            title=f"Appointment: {args.get('reason', '')}".strip(": "),
            description=args.get("reason", ""),
            call_log=call_log,
        )
    except ValueError as exc:
        return {"result": str(exc)}

    # Async sync to external calendar — import locally so worker doesn't pull celery
    # at import time.
    try:
        from apps.voice_agent.tasks import sync_calendar_event

        sync_calendar_event.delay(str(event.id))
    except Exception:  # noqa: BLE001
        logger.exception("sync_calendar_event_dispatch_failed", extra={"event_id": str(event.id)})

    return {
        "result": (
            f"Appointment booked for {args.get('attendee_name', '')} "
            f"on {date.strftime('%B %d, %Y')} at {time_str}. "
            f"Duration: {duration} minutes."
        )
    }


def request_callback(
    website_id: str, args: dict[str, Any], external_call_id: str = ""
) -> dict[str, str]:
    """Schedule a human callback to the contact."""
    remind_at = tz.now() + timedelta(hours=1)
    preferred = args.get("preferred_time", "")
    if preferred:
        parsed = parse_datetime(preferred)
        if parsed:
            remind_at = parsed

    call_log = _find_call_log(external_call_id)

    reminder = CallService.create_callback_reminder(
        website_id=website_id,
        contact_name=args.get("contact_name", ""),
        contact_phone=args.get("contact_phone", ""),
        remind_at=remind_at,
        reason=args.get("reason", ""),
        call_log=call_log,
    )

    try:
        from apps.voice_agent.tasks import send_callback_notification

        send_callback_notification.delay(str(reminder.id))
    except Exception:  # noqa: BLE001
        logger.exception(
            "send_callback_notification_dispatch_failed",
            extra={"reminder_id": str(reminder.id)},
        )

    return {
        "result": (
            f"Callback reminder set for {args.get('contact_name', '')}. "
            f"Someone will call you back."
        )
    }


def check_availability(website_id: str, args: dict[str, Any]) -> dict[str, str]:
    """Return free appointment slots for a date."""
    date = parse_date(args.get("date", ""))
    if not date:
        return {"result": "I need a valid date to check availability."}

    slots = CalendarService.get_available_slots(website_id=website_id, date=date)
    if not slots:
        return {
            "result": (
                f"No available slots on {date.strftime('%B %d, %Y')}. "
                "Would you like to try another date?"
            )
        }

    slot_list = ", ".join(f"{s['start']}-{s['end']}" for s in slots[:6])
    more = f" and {len(slots) - 6} more" if len(slots) > 6 else ""
    return {
        "result": f"Available slots on {date.strftime('%B %d, %Y')}: {slot_list}{more}"
    }
