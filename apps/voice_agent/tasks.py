"""
Celery tasks for voice agent async operations.

- Callback reminder notifications
- Calendar event sync to Google Calendar / Outlook
- Periodic reminder checks
- Outbound dialer (campaign fan-out + per-call placement)
"""

import json
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("apps")


# ── Outbound dialer ────────────────────────────────────────────────────────────


def _within_business_hours(config) -> bool:
    """Return True when current time is inside the website's business hours.

    ``config.business_hours`` is a JSON dict like
    ``{"monday": {"start": "09:00", "end": "17:00"}}``. Missing days = closed.
    """
    if not config or not config.business_hours:
        return True  # no restriction configured

    try:
        import zoneinfo

        tzinfo = zoneinfo.ZoneInfo(config.timezone or "UTC")
    except Exception:  # noqa: BLE001
        tzinfo = timezone.utc

    now_local = timezone.now().astimezone(tzinfo)
    day_key = now_local.strftime("%A").lower()
    window = config.business_hours.get(day_key)
    if not window:
        return False
    start = window.get("start", "00:00")
    end = window.get("end", "23:59")
    current = now_local.strftime("%H:%M")
    return start <= current <= end


@shared_task(name="apps.voice_agent.tasks.dispatch_campaign")
def dispatch_campaign(campaign_id: str) -> dict:
    """Fan a running campaign out into individual ``place_outbound_call`` jobs.

    Throttled by ``campaign.calls_per_minute``. Self-reschedules every 60s while
    pending targets remain. Stops if the campaign is paused, completed, or
    outside business hours (when ``respect_business_hours`` is set).
    """
    from apps.voice_agent.models import AgentConfig, CallCampaign, CallTarget

    try:
        campaign = CallCampaign.objects.select_related("website").get(id=campaign_id)
    except CallCampaign.DoesNotExist:
        logger.warning("dispatch_campaign_missing", extra={"campaign_id": campaign_id})
        return {"status": "missing"}

    if campaign.status != CallCampaign.STATUS_RUNNING:
        logger.info(
            "dispatch_campaign_not_running",
            extra={"campaign_id": campaign_id, "status": campaign.status},
        )
        return {"status": campaign.status}

    if campaign.respect_business_hours:
        config = AgentConfig.objects.filter(website=campaign.website).first()
        if not _within_business_hours(config):
            logger.info(
                "dispatch_campaign_outside_hours", extra={"campaign_id": campaign_id}
            )
            dispatch_campaign.apply_async(args=[campaign_id], countdown=600)
            return {"status": "outside_hours"}

    rate = max(1, int(campaign.calls_per_minute or 10))
    spacing = 60.0 / rate

    with transaction.atomic():
        targets = list(
            CallTarget.objects.select_for_update(skip_locked=True)
            .filter(campaign=campaign, status=CallTarget.STATUS_PENDING)
            .order_by("created_at")[:rate]
        )
        for t in targets:
            t.status = CallTarget.STATUS_QUEUED
            t.save(update_fields=["status", "updated_at"])

    for index, target in enumerate(targets):
        place_outbound_call.apply_async(
            args=[str(target.id)],
            countdown=int(index * spacing),
        )

    remaining = CallTarget.objects.filter(
        campaign=campaign, status=CallTarget.STATUS_PENDING
    ).exists()

    if remaining:
        dispatch_campaign.apply_async(args=[campaign_id], countdown=60)
    else:
        in_flight = CallTarget.objects.filter(
            campaign=campaign,
            status__in=[
                CallTarget.STATUS_QUEUED,
                CallTarget.STATUS_DIALING,
                CallTarget.STATUS_IN_PROGRESS,
            ],
        ).exists()
        if not in_flight:
            campaign.status = CallCampaign.STATUS_COMPLETED
            campaign.save(update_fields=["status", "updated_at"])

    return {"status": "ok", "queued": len(targets)}


@shared_task(
    name="apps.voice_agent.tasks.place_outbound_call",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def place_outbound_call(self, target_id: str) -> dict:
    """Place a single outbound call: create CallLog, dispatch agent, ask LiveKit
    to dial the recipient via the Telnyx outbound trunk."""
    from apps.voice_agent.models import (
        CallLog,
        CallTarget,
        DoNotCallEntry,
    )
    from apps.voice_agent.services.livekit_service import LiveKitService

    try:
        target = CallTarget.objects.select_related(
            "campaign", "campaign__from_number", "campaign__website"
        ).get(id=target_id)
    except CallTarget.DoesNotExist:
        logger.warning("place_outbound_call_missing_target", extra={"target_id": target_id})
        return {"status": "missing"}

    campaign = target.campaign

    # DNC enforcement
    if DoNotCallEntry.objects.filter(phone=target.phone).exists():
        target.status = CallTarget.STATUS_DO_NOT_CALL
        target.last_error = "phone on do-not-call list"
        target.save(update_fields=["status", "last_error", "updated_at"])
        logger.info("place_outbound_call_dnc", extra={"target_id": target_id})
        return {"status": "dnc"}

    # Usage limit enforcement — stop before placing if the plan cap is hit.
    try:
        from apps.voice_agent.services.usage_service import enforce_usage_limit
        enforce_usage_limit(campaign.website_id)
    except Exception as exc:  # noqa: BLE001
        target.status = CallTarget.STATUS_FAILED
        target.last_error = str(exc)[:500]
        target.save(update_fields=["status", "last_error", "updated_at"])
        logger.warning(
            "place_outbound_call_usage_limit",
            extra={"target_id": target_id, "error": str(exc)},
        )
        return {"status": "usage_limit_exceeded"}

    if campaign.status != campaign.STATUS_RUNNING:
        target.status = CallTarget.STATUS_PENDING
        target.save(update_fields=["status", "updated_at"])
        return {"status": "campaign_not_running"}

    from_number = campaign.from_number
    if not from_number.livekit_outbound_trunk_id:
        msg = "from_number missing livekit_outbound_trunk_id; run setup_livekit_outbound_trunk"
        logger.error(
            "place_outbound_call_missing_trunk",
            extra={"target_id": target_id, "from_number_id": str(from_number.id)},
        )
        target.status = CallTarget.STATUS_FAILED
        target.last_error = msg
        target.save(update_fields=["status", "last_error", "updated_at"])
        return {"status": "no_trunk"}

    target.status = CallTarget.STATUS_DIALING
    target.attempt_count = (target.attempt_count or 0) + 1
    target.last_attempt_at = timezone.now()
    target.save(
        update_fields=["status", "attempt_count", "last_attempt_at", "updated_at"]
    )

    call_log = CallLog.objects.create(
        website=campaign.website,
        direction=CallLog.DIRECTION_OUTBOUND,
        status=CallLog.STATUS_RINGING,
        caller_phone=target.phone,
        caller_name=target.name,
        campaign=campaign,
        target=target,
    )

    metadata = json.dumps(
        {
            "website_id": str(campaign.website_id),
            "campaign_id": str(campaign.id),
            "target_id": str(target.id),
            "call_log_id": str(call_log.id),
            "welcome": campaign.welcome_message,
            "recipient_name": target.name,
        }
    )
    room_name = f"voice-agent-out-{call_log.id}"
    call_log.external_call_id = room_name
    call_log.save(update_fields=["external_call_id", "updated_at"])

    try:
        LiveKitService.create_room(name=room_name, metadata=metadata)
        LiveKitService.dispatch_agent(
            room_name=room_name,
            agent_name=getattr(settings, "LIVEKIT_AGENT_NAME", "ftb-voice-agent"),
            metadata=metadata,
        )
        LiveKitService.create_sip_participant(
            room_name=room_name,
            trunk_id=from_number.livekit_outbound_trunk_id,
            to_phone=target.phone,
            from_phone=from_number.number,
            participant_identity=f"sip-{target.id}",
            participant_name=target.name or target.phone,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "place_outbound_call_failed",
            extra={"target_id": target_id, "call_log_id": str(call_log.id)},
        )
        call_log.status = CallLog.STATUS_FAILED
        call_log.save(update_fields=["status", "updated_at"])
        target.last_error = str(exc)[:500]
        if target.attempt_count < target.max_attempts:
            target.status = CallTarget.STATUS_PENDING
            target.save(update_fields=["status", "last_error", "updated_at"])
            try:
                self.retry(exc=exc, countdown=60 * target.attempt_count)
            except self.MaxRetriesExceededError:
                target.status = CallTarget.STATUS_FAILED
                target.save(update_fields=["status", "updated_at"])
        else:
            target.status = CallTarget.STATUS_FAILED
            target.save(update_fields=["status", "last_error", "updated_at"])
        return {"status": "error", "error": str(exc)}

    return {"status": "dialing", "call_log_id": str(call_log.id)}


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


@shared_task(name="apps.voice_agent.tasks.queue_health_check")
def queue_health_check() -> dict:
    """Monitor the ``ai`` Celery queue depth and report metrics.

    Returns a dict with queue depth and a list of any stalled tasks.
    Wire the return value into your monitoring stack (Sentry, Datadog, etc.)
    or have a periodic check fire an alert when ``depth > threshold``.
    """
    from django.core.cache import cache

    result = {"status": "ok", "queue": "ai", "depth": 0, "stalled_tasks": []}

    try:
        from config.celery import app as celery_app

        # Inspect active + reserved tasks on the `ai` queue
        inspector = celery_app.control.inspect()
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}

        total_active = sum(len(tasks) for tasks in active.values())
        total_reserved = sum(len(tasks) for tasks in reserved.values())
        depth = total_active + total_reserved
        result["depth"] = depth

        # Check for stalled extraction tasks (running > 5 minutes)
        import time

        for worker, tasks in active.items():
            for task in tasks:
                # livekit-agents tasks may run for entire call duration — skip
                if "place_outbound_call" in task.get("name", ""):
                    continue
                started = task.get("time_start", 0)
                if started and (time.time() - started) > 300:
                    result["stalled_tasks"].append({
                        "id": task.get("id", ""),
                        "name": task.get("name", ""),
                        "worker": worker,
                        "running_seconds": int(time.time() - started),
                    })

        # Cache the result for dashboard polling
        cache.set("voice_agent:queue_health", result, timeout=120)

        if depth > 50:
            logger.warning(
                "voice_queue_depth_high",
                extra={"depth": depth, "stalled": len(result["stalled_tasks"])},
            )
        if result["stalled_tasks"]:
            result["status"] = "degraded"
            logger.warning(
                "voice_queue_stalled_tasks",
                extra={"stalled": result["stalled_tasks"]},
            )

    except Exception as e:  # noqa: BLE001
        logger.warning("queue_health_check_failed", extra={"error": str(e)})
        result["status"] = "error"
        result["error"] = str(e)

    return result


@shared_task(name="apps.voice_agent.tasks.reconcile_monthly_usage")
def reconcile_monthly_usage() -> dict:
    """Nightly reconciler: rebuild VoiceUsageMonthly from CallLog.

    If a ``record_call`` increment was lost (worker crash, Redis outage),
    this task recovers the correct totals. Idempotent — safe to run repeatedly.
    """
    from apps.voice_agent.services import usage_service
    from apps.websites.models import Website

    ym = timezone.now().strftime("%Y-%m")
    websites = (
        Website.objects
        .filter(call_logs__created_at__year=int(ym[:4]), call_logs__created_at__month=int(ym[5:]))
        .distinct()
        .values_list("id", flat=True)
    )

    count = 0
    for wid in websites:
        try:
            usage_service.rebuild_month(wid, ym)
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "reconcile_monthly_usage_failed",
                extra={"website_id": str(wid), "error": str(e)},
            )

    logger.info("reconcile_monthly_usage_done", extra={"month": ym, "websites": count})
    return {"month": ym, "websites_reconciled": count}

