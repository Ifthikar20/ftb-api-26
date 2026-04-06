"""
Celery tasks for voice agent async operations.

- Callback reminder notifications
- Calendar event sync to Google Calendar / Outlook
- Periodic reminder checks
"""

import logging

from celery import shared_task

logger = logging.getLogger("apps")


@shared_task(name="apps.voice_agent.tasks.send_callback_notification")
def send_callback_notification(reminder_id):
    """Send a notification for a callback reminder (email + in-app)."""
    from apps.voice_agent.models import CallbackReminder

    try:
        reminder = CallbackReminder.objects.select_related(
            "website", "assigned_to"
        ).get(id=reminder_id)
    except CallbackReminder.DoesNotExist:
        logger.warning("callback_reminder_not_found", extra={"reminder_id": reminder_id})
        return

    # Create in-app notification
    try:
        from apps.notifications.models import Notification

        recipient = reminder.assigned_to or reminder.website.owner
        if recipient:
            Notification.objects.create(
                user=recipient,
                title="Callback Reminder",
                message=(
                    f"Reminder to call back {reminder.contact_name} "
                    f"at {reminder.contact_phone}. "
                    f"Reason: {reminder.reason or 'No reason specified.'}"
                ),
                category="voice_agent",
                link=f"/voice-agent/{reminder.website_id}",
            )
    except Exception as e:
        logger.warning("callback_notification_failed", extra={"error": str(e)})

    # Send email notification
    try:
        from django.conf import settings as django_settings

        if django_settings.SENDGRID_API_KEY:
            from apps.notifications.services.email_service import send_notification_email

            recipient = reminder.assigned_to or reminder.website.owner
            if recipient and hasattr(recipient, "email"):
                send_notification_email(
                    to_email=recipient.email,
                    subject=f"Callback Reminder: {reminder.contact_name}",
                    body=(
                        f"You have a callback reminder for {reminder.contact_name} "
                        f"({reminder.contact_phone}).\n\n"
                        f"Reason: {reminder.reason or 'Not specified'}\n"
                        f"Scheduled for: {reminder.remind_at.strftime('%B %d, %Y at %I:%M %p')}"
                    ),
                )
    except Exception as e:
        logger.warning("callback_email_failed", extra={"error": str(e)})

    reminder.status = "sent"
    reminder.save(update_fields=["status", "updated_at"])

    logger.info(
        "callback_notification_sent",
        extra={"reminder_id": reminder_id, "contact": reminder.contact_name},
    )


@shared_task(name="apps.voice_agent.tasks.sync_calendar_event")
def sync_calendar_event(event_id):
    """Sync a calendar event to Google Calendar if integration is active."""
    from apps.voice_agent.models import CalendarEvent

    try:
        event = CalendarEvent.objects.select_related("website").get(id=event_id)
    except CalendarEvent.DoesNotExist:
        logger.warning("calendar_event_not_found", extra={"event_id": event_id})
        return

    # Check for Google Calendar integration
    try:
        from apps.websites.models import Integration

        integration = Integration.objects.get(
            website=event.website, type="google_calendar", is_active=True
        )
    except Exception:
        logger.info("no_google_calendar_integration", extra={"website_id": str(event.website_id)})
        return

    # Sync to Google Calendar
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=integration.access_token,
            refresh_token=integration.refresh_token,
            client_id=integration.client_id,
            client_secret=integration.client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("calendar", "v3", credentials=creds)

        gcal_event = {
            "summary": event.title,
            "description": event.description,
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": event.timezone,
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": event.timezone,
            },
            "attendees": [],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30},
                    {"method": "email", "minutes": 60},
                ],
            },
        }

        if event.attendee_email:
            gcal_event["attendees"].append({"email": event.attendee_email})

        result = service.events().insert(calendarId="primary", body=gcal_event).execute()

        event.google_event_id = result.get("id", "")
        event.save(update_fields=["google_event_id", "updated_at"])

        logger.info(
            "calendar_synced_google",
            extra={"event_id": event_id, "google_id": event.google_event_id},
        )
    except Exception as e:
        logger.warning(
            "google_calendar_sync_failed",
            extra={"event_id": event_id, "error": str(e)},
        )


@shared_task(name="apps.voice_agent.tasks.extract_call_data")
def extract_call_data(call_log_id):
    """
    Post-call extraction: analyze transcript with self-hosted LLM.
    Extracts caller info, todos, action items, sentiment, and summary.
    Runs automatically after every completed call.
    """
    from apps.voice_agent.models import CallLog

    try:
        call_log = CallLog.objects.get(id=call_log_id)
    except CallLog.DoesNotExist:
        logger.warning("extract_call_not_found", extra={"call_id": call_log_id})
        return

    if not call_log.transcript:
        logger.info("extract_skipped_no_transcript", extra={"call_id": call_log_id})
        return

    from apps.voice_agent.services.extraction_service import ExtractionService

    try:
        extraction = ExtractionService.extract_from_transcript(call_log)
        if extraction:
            logger.info(
                "call_extraction_complete",
                extra={
                    "call_id": call_log_id,
                    "category": extraction.call_category,
                    "todos": call_log.todos.count(),
                },
            )
    except Exception as e:
        logger.error(
            "call_extraction_failed",
            extra={"call_id": call_log_id, "error": str(e)},
        )


@shared_task(name="apps.voice_agent.tasks.check_due_reminders")
def check_due_reminders():
    """Periodic task: find and send notifications for due callback reminders."""
    from django.utils import timezone

    from apps.voice_agent.models import CallbackReminder

    due = CallbackReminder.objects.filter(
        status=CallbackReminder.STATUS_PENDING,
        remind_at__lte=timezone.now(),
    )

    for reminder in due:
        send_callback_notification.delay(str(reminder.id))

    if due.exists():
        logger.info("due_reminders_dispatched", extra={"count": due.count()})
