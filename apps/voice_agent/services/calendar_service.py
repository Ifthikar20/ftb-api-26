"""
Calendar service for the voice agent.

Handles appointment scheduling, availability checking, slot blocking,
and external calendar sync (Google Calendar / Outlook).
"""

import logging
from datetime import datetime, timedelta

from django.utils import timezone

from apps.voice_agent.models import AgentConfig, CalendarEvent

logger = logging.getLogger("apps")


class CalendarService:
    """Manage appointments and calendar availability."""

    @staticmethod
    def get_available_slots(*, website_id, date, duration_minutes=None):
        """
        Return available time slots for a given date.
        Checks against existing appointments and business hours.
        """
        try:
            config = AgentConfig.objects.get(website_id=website_id)
        except AgentConfig.DoesNotExist:
            return []

        if duration_minutes is None:
            duration_minutes = config.appointment_duration_minutes

        day_name = date.strftime("%A").lower()
        hours = config.business_hours.get(day_name)
        if not hours:
            return []

        start_hour, start_min = map(int, hours["start"].split(":"))
        end_hour, end_min = map(int, hours["end"].split(":"))

        # Build all possible slots
        slots = []
        current = datetime.combine(date, datetime.min.time().replace(
            hour=start_hour, minute=start_min
        ))
        day_end = datetime.combine(date, datetime.min.time().replace(
            hour=end_hour, minute=end_min
        ))

        while current + timedelta(minutes=duration_minutes) <= day_end:
            slots.append({
                "start": current.strftime("%H:%M"),
                "end": (current + timedelta(minutes=duration_minutes)).strftime("%H:%M"),
            })
            current += timedelta(minutes=duration_minutes)

        # Remove slots that conflict with existing appointments
        existing = CalendarEvent.objects.filter(
            website_id=website_id,
            start_time__date=date,
            status__in=[
                CalendarEvent.STATUS_SCHEDULED,
                CalendarEvent.STATUS_CONFIRMED,
            ],
        ).values_list("start_time", "end_time")

        booked_ranges = [
            (s.strftime("%H:%M"), e.strftime("%H:%M")) for s, e in existing
        ]

        available = []
        for slot in slots:
            conflict = False
            for booked_start, booked_end in booked_ranges:
                if slot["start"] < booked_end and slot["end"] > booked_start:
                    conflict = True
                    break
            if not conflict:
                available.append(slot)

        return available

    @staticmethod
    def book_appointment(
        *,
        website_id,
        attendee_name,
        attendee_phone,
        start_time,
        end_time=None,
        attendee_email="",
        title="",
        description="",
        call_log=None,
        assigned_to=None,
        tz="UTC",
    ):
        """Book a new appointment and block the calendar slot."""
        try:
            config = AgentConfig.objects.get(website_id=website_id)
        except AgentConfig.DoesNotExist:
            raise ValueError("Voice agent not configured for this website.")

        if end_time is None:
            end_time = start_time + timedelta(minutes=config.appointment_duration_minutes)

        if not title:
            title = f"Appointment with {attendee_name}"

        # Check for conflicts
        conflicts = CalendarEvent.objects.filter(
            website_id=website_id,
            status__in=[
                CalendarEvent.STATUS_SCHEDULED,
                CalendarEvent.STATUS_CONFIRMED,
            ],
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()

        if conflicts:
            raise ValueError("This time slot is already booked.")

        event = CalendarEvent.objects.create(
            website_id=website_id,
            call_log=call_log,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            timezone=tz,
            attendee_name=attendee_name,
            attendee_phone=attendee_phone,
            attendee_email=attendee_email,
            assigned_to=assigned_to,
        )

        logger.info(
            "appointment_booked",
            extra={
                "event_id": str(event.id),
                "website_id": str(website_id),
                "attendee": attendee_name,
                "start": start_time.isoformat(),
            },
        )

        return event

    @staticmethod
    def cancel_appointment(event_id, website_id):
        """Cancel an appointment and free the slot."""
        try:
            event = CalendarEvent.objects.get(id=event_id, website_id=website_id)
        except CalendarEvent.DoesNotExist:
            raise ValueError("Appointment not found.")

        if event.status in (CalendarEvent.STATUS_CANCELLED, CalendarEvent.STATUS_COMPLETED):
            raise ValueError(f"Cannot cancel an appointment that is already {event.status}.")

        event.status = CalendarEvent.STATUS_CANCELLED
        event.save(update_fields=["status", "updated_at"])

        logger.info(
            "appointment_cancelled",
            extra={"event_id": str(event_id), "website_id": str(website_id)},
        )

        return event

    @staticmethod
    def update_status(event_id, website_id, new_status):
        """Update appointment status."""
        try:
            event = CalendarEvent.objects.get(id=event_id, website_id=website_id)
        except CalendarEvent.DoesNotExist:
            raise ValueError("Appointment not found.")

        valid_statuses = [c[0] for c in CalendarEvent.STATUS_CHOICES]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        event.status = new_status
        event.save(update_fields=["status", "updated_at"])
        return event

    @staticmethod
    def get_upcoming(website_id, days=7):
        """Get upcoming appointments for the next N days."""
        now = timezone.now()
        cutoff = now + timedelta(days=days)
        return CalendarEvent.objects.filter(
            website_id=website_id,
            start_time__gte=now,
            start_time__lte=cutoff,
            status__in=[
                CalendarEvent.STATUS_SCHEDULED,
                CalendarEvent.STATUS_CONFIRMED,
            ],
        ).select_related("call_log", "assigned_to")
