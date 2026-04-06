"""
Call management service.

Handles call log creation, webhook processing, caller identification,
and linking calls to leads.
"""

import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.voice_agent.models import CallbackReminder, CallLog

logger = logging.getLogger("apps")


class CallService:
    """Process and manage voice call data."""

    @staticmethod
    def get_calls(website_id, *, status=None, direction=None, phone=None):
        """List call logs with optional filters."""
        qs = CallLog.objects.filter(website_id=website_id)
        if status:
            qs = qs.filter(status=status)
        if direction:
            qs = qs.filter(direction=direction)
        if phone:
            qs = qs.filter(caller_phone__icontains=phone)
        return qs.select_related("lead")

    @staticmethod
    def get_call(website_id, call_id):
        """Get a single call log."""
        try:
            return CallLog.objects.select_related("lead").get(
                id=call_id, website_id=website_id
            )
        except CallLog.DoesNotExist:
            from core.exceptions import ResourceNotFound
            raise ResourceNotFound("Call log not found.") from None

    @staticmethod
    def process_call_started(website_id, data):
        """Handle call_started webhook from Retell AI."""
        call_log, _ = CallLog.objects.update_or_create(
            retell_call_id=data["call_id"],
            defaults={
                "website_id": website_id,
                "direction": data.get("direction", "inbound"),
                "status": CallLog.STATUS_IN_PROGRESS,
                "caller_phone": data.get("from_number", ""),
                "started_at": timezone.now(),
            },
        )

        logger.info(
            "call_started",
            extra={
                "call_id": str(call_log.id),
                "retell_call_id": data["call_id"],
                "caller": data.get("from_number", ""),
            },
        )

        return call_log

    @staticmethod
    def process_call_ended(website_id, data):
        """Handle call_ended webhook from Retell AI with transcript and extracted data."""
        call_data = data.get("call", {})
        retell_call_id = data.get("call_id", call_data.get("call_id", ""))

        transcript = call_data.get("transcript", "")
        if isinstance(transcript, list):
            transcript = "\n".join(
                f"{t.get('role', 'unknown')}: {t.get('content', '')}"
                for t in transcript
            )

        defaults = {
            "website_id": website_id,
            "status": CallLog.STATUS_COMPLETED,
            "ended_at": timezone.now(),
            "transcript": transcript,
            "summary": call_data.get("call_analysis", {}).get("call_summary", ""),
            "sentiment": call_data.get("call_analysis", {}).get("user_sentiment", ""),
            "call_intent": call_data.get("call_analysis", {}).get("call_intent", ""),
            "extracted_data": call_data.get("call_analysis", {}).get("custom_analysis_data", {}),
        }

        # Calculate duration
        start_ts = call_data.get("start_timestamp")
        end_ts = call_data.get("end_timestamp")
        if start_ts and end_ts:
            defaults["duration_seconds"] = int((end_ts - start_ts) / 1000)

        # Extract caller info from analysis
        extracted = defaults["extracted_data"]
        if isinstance(extracted, dict):
            defaults["caller_name"] = extracted.get("caller_name", "")
            defaults["caller_email"] = extracted.get("caller_email", "")
            defaults["caller_company"] = extracted.get("caller_company", "")

        call_log, _ = CallLog.objects.update_or_create(
            retell_call_id=retell_call_id,
            defaults=defaults,
        )

        # Try to link to an existing lead by phone
        if call_log.caller_phone:
            CallService._link_to_lead(call_log)

        logger.info(
            "call_ended",
            extra={
                "call_id": str(call_log.id),
                "duration": call_log.duration_seconds,
                "sentiment": call_log.sentiment,
            },
        )

        # Trigger async post-call extraction (todos, caller info, summary)
        if call_log.transcript:
            from apps.voice_agent.tasks import extract_call_data

            extract_call_data.delay(str(call_log.id))

        return call_log

    @staticmethod
    def process_call_analyzed(website_id, data):
        """Handle post-call analysis webhook with deeper insights."""
        retell_call_id = data.get("call_id", "")
        analysis = data.get("call_analysis", {})

        try:
            call_log = CallLog.objects.get(retell_call_id=retell_call_id)
        except CallLog.DoesNotExist:
            logger.warning("call_analyzed_orphan", extra={"retell_call_id": retell_call_id})
            return None

        if analysis.get("call_summary"):
            call_log.summary = analysis["call_summary"]
        if analysis.get("user_sentiment"):
            call_log.sentiment = analysis["user_sentiment"]
        if analysis.get("custom_analysis_data"):
            call_log.extracted_data = {
                **call_log.extracted_data,
                **analysis["custom_analysis_data"],
            }

        call_log.save(update_fields=["summary", "sentiment", "extracted_data", "updated_at"])
        return call_log

    @staticmethod
    def _link_to_lead(call_log):
        """Try to link a call to an existing lead by phone number."""
        from apps.analytics.models import Visitor
        from apps.leads.models import Lead

        # Check if any visitor/lead has this phone in extracted data
        leads = Lead.objects.filter(
            website_id=call_log.website_id,
        ).select_related("visitor")

        for lead in leads:
            if lead.email and call_log.caller_email and lead.email == call_log.caller_email:
                call_log.lead = lead
                call_log.save(update_fields=["lead"])
                return

    @staticmethod
    def create_callback_reminder(
        *,
        website_id,
        contact_name,
        contact_phone,
        remind_at,
        reason="",
        call_log=None,
        assigned_to=None,
    ):
        """Create a callback reminder."""
        reminder = CallbackReminder.objects.create(
            website_id=website_id,
            call_log=call_log,
            contact_name=contact_name,
            contact_phone=contact_phone,
            reason=reason,
            remind_at=remind_at,
            assigned_to=assigned_to,
        )

        logger.info(
            "callback_reminder_created",
            extra={
                "reminder_id": str(reminder.id),
                "contact": contact_name,
                "remind_at": remind_at.isoformat(),
            },
        )

        return reminder

    @staticmethod
    def get_pending_reminders(website_id):
        """Get all pending callback reminders."""
        return CallbackReminder.objects.filter(
            website_id=website_id,
            status=CallbackReminder.STATUS_PENDING,
        ).select_related("call_log", "assigned_to")

    @staticmethod
    def dismiss_reminder(reminder_id, website_id):
        """Dismiss a callback reminder."""
        try:
            reminder = CallbackReminder.objects.get(id=reminder_id, website_id=website_id)
        except CallbackReminder.DoesNotExist:
            from core.exceptions import ResourceNotFound
            raise ResourceNotFound("Reminder not found.") from None

        reminder.status = CallbackReminder.STATUS_DISMISSED
        reminder.save(update_fields=["status", "updated_at"])
        return reminder

    @staticmethod
    def complete_reminder(reminder_id, website_id, notes=""):
        """Mark a callback reminder as completed."""
        try:
            reminder = CallbackReminder.objects.get(id=reminder_id, website_id=website_id)
        except CallbackReminder.DoesNotExist:
            from core.exceptions import ResourceNotFound
            raise ResourceNotFound("Reminder not found.") from None

        reminder.status = CallbackReminder.STATUS_COMPLETED
        if notes:
            reminder.notes = notes
        reminder.save(update_fields=["status", "notes", "updated_at"])
        return reminder

    @staticmethod
    def get_call_stats(website_id):
        """Get aggregate call statistics."""
        from django.db.models import Avg, Count, Q, Sum

        qs = CallLog.objects.filter(website_id=website_id)
        stats = qs.aggregate(
            total_calls=Count("id"),
            completed_calls=Count("id", filter=Q(status=CallLog.STATUS_COMPLETED)),
            missed_calls=Count("id", filter=Q(status=CallLog.STATUS_MISSED)),
            total_duration=Sum("duration_seconds"),
            avg_duration=Avg("duration_seconds"),
            inbound=Count("id", filter=Q(direction=CallLog.DIRECTION_INBOUND)),
            outbound=Count("id", filter=Q(direction=CallLog.DIRECTION_OUTBOUND)),
        )
        stats["total_duration"] = stats["total_duration"] or 0
        stats["avg_duration"] = round(stats["avg_duration"] or 0)

        # Sentiment breakdown
        sentiment_counts = (
            qs.filter(sentiment__gt="")
            .values("sentiment")
            .annotate(count=Count("id"))
        )
        stats["sentiment"] = {s["sentiment"]: s["count"] for s in sentiment_counts}

        # Appointments booked from calls
        from apps.voice_agent.models import CalendarEvent

        stats["appointments_booked"] = CalendarEvent.objects.filter(
            website_id=website_id,
            call_log__isnull=False,
        ).count()

        return stats
