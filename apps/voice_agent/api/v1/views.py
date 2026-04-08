import logging
from datetime import datetime

from django.conf import settings
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.voice_agent.api.v1.serializers import (
    AgentConfigSerializer,
    AgentContextDocumentSerializer,
    CalendarEventSerializer,
    CallbackReminderSerializer,
    CallExtractionSerializer,
    CallLogSerializer,
    CallTodoSerializer,
    PhoneNumberSerializer,
)
from apps.voice_agent.models import AgentConfig, AgentContextDocument, CalendarEvent, PhoneNumber
from apps.voice_agent.services.calendar_service import CalendarService
from apps.voice_agent.services.call_service import CallService
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination

logger = logging.getLogger("apps")


# ── Agent Configuration ──────────────────────────────────────────────────────


class AgentConfigView(APIView):
    """Get or update voice agent configuration for a website."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = AgentConfig.objects.get_or_create(
            website=website,
            defaults={
                "business_hours": {
                    "monday": {"start": "09:00", "end": "17:00"},
                    "tuesday": {"start": "09:00", "end": "17:00"},
                    "wednesday": {"start": "09:00", "end": "17:00"},
                    "thursday": {"start": "09:00", "end": "17:00"},
                    "friday": {"start": "09:00", "end": "17:00"},
                },
            },
        )
        return Response(AgentConfigSerializer(config).data)

    def put(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = AgentConfig.objects.get_or_create(
            website=website,
            defaults={"business_hours": {}},
        )
        serializer = AgentConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # If agent exists in Retell, update it
        if config.retell_agent_id and config.is_active:
            try:
                from apps.voice_agent.services.retell_service import RetellService

                RetellService.update_agent(
                    config.retell_agent_id,
                    general_prompt=config.system_prompt,
                    begin_message=config.greeting_message,
                    agent_name=config.business_name or website.name,
                )
            except Exception as e:
                logger.warning("retell_agent_update_failed", extra={"error": str(e)})

        return Response(AgentConfigSerializer(config).data)


def _get_backend():
    """Return the configured voice agent backend ('retell', 'livekit', or 'selfhosted')."""
    from django.conf import settings as s
    backend = getattr(s, "VOICE_AGENT_BACKEND", "selfhosted")
    if backend not in ("retell", "livekit", "selfhosted"):
        logger.warning("invalid_voice_backend", extra={"backend": backend})
        return "selfhosted"
    return backend


class AgentActivateView(APIView):
    """Activate or deactivate the voice agent. Supports both Retell AI and self-hosted LiveKit."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = AgentConfig.objects.get_or_create(
            website=website, defaults={"business_hours": {}}
        )
        action = request.data.get("action", "activate")

        if action == "activate":
            backend = _get_backend()

            if backend in ("livekit", "selfhosted"):
                # LiveKit / Self-hosted: no external agent creation needed — the
                # agent worker picks up calls via SIP trunk or direct connection.
                config.is_active = True
                config.save(update_fields=["is_active", "updated_at"])
                cost = "~$0.017" if backend == "livekit" else "~$0.003-0.005"
                return Response(
                    {
                        **AgentConfigSerializer(config).data,
                        "backend": backend,
                        "cost_per_min": cost,
                        "message": (
                            f"Voice agent activated ({backend}). "
                            "Ensure the agent worker is running and "
                            "SIP trunk is configured."
                        ),
                    },
                    status=status.HTTP_201_CREATED,
                )

            # Retell AI backend
            if config.retell_agent_id:
                config.is_active = True
                config.save(update_fields=["is_active", "updated_at"])
                return Response(AgentConfigSerializer(config).data)

            try:
                from apps.voice_agent.services.retell_service import RetellService

                result = RetellService.create_agent(
                    agent_name=config.business_name or website.name,
                    system_prompt=config.system_prompt,
                    greeting_message=config.greeting_message,
                )
                config.retell_agent_id = result.get("agent_id", "")
                config.is_active = True
                config.save(update_fields=["retell_agent_id", "is_active", "updated_at"])
            except Exception as e:
                return Response(
                    {"error": f"Failed to create voice agent: {str(e)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            return Response(AgentConfigSerializer(config).data, status=status.HTTP_201_CREATED)

        elif action == "deactivate":
            config.is_active = False
            config.save(update_fields=["is_active", "updated_at"])
            return Response(AgentConfigSerializer(config).data)

        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)


class WebCallView(APIView):
    """Create a browser-based voice call session. Supports all three backends."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            config = AgentConfig.objects.get(website=website, is_active=True)
        except AgentConfig.DoesNotExist:
            return Response(
                {"error": "Voice agent is not active for this website."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        backend = _get_backend()

        if backend in ("livekit", "selfhosted"):
            try:
                from apps.voice_agent.services.livekit_service import LiveKitService

                result = LiveKitService.create_web_call_token(
                    website_id=str(website_id),
                    user_id=str(request.user.id),
                )
                if not result:
                    return Response(
                        {"error": "LiveKit API not available."},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
                return Response(result)
            except Exception as e:
                return Response(
                    {"error": f"Failed to create web call: {str(e)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        # Retell AI backend
        if not config.retell_agent_id:
            return Response(
                {"error": "Voice agent has not been created yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.voice_agent.services.retell_service import RetellService

            result = RetellService.create_web_call(
                agent_id=config.retell_agent_id,
                metadata={"website_id": str(website_id), "user_id": str(request.user.id)},
            )
            return Response(result)
        except Exception as e:
            return Response(
                {"error": f"Failed to create web call: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


# ── Call Logs ────────────────────────────────────────────────────────────────


class CallLogListView(APIView):
    """List call logs for a website."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        call_status = request.query_params.get("status")
        direction = request.query_params.get("direction")
        phone = request.query_params.get("phone")
        calls = CallService.get_calls(
            website_id, status=call_status, direction=direction, phone=phone
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(calls, request)
        return paginator.get_paginated_response(CallLogSerializer(page, many=True).data)


class CallLogDetailView(APIView):
    """Get a single call log with full transcript."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, call_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        call = CallService.get_call(website_id, call_id)
        return Response(CallLogSerializer(call).data)


class CallStatsView(APIView):
    """Get aggregate call statistics."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        stats = CallService.get_call_stats(website_id)
        return Response(stats)


# ── Calendar / Appointments ──────────────────────────────────────────────────


class CalendarEventListView(APIView):
    """List and create calendar events."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        event_status = request.query_params.get("status")
        days = int(request.query_params.get("days", 30))
        events = CalendarService.get_upcoming(website_id, days=days)
        if event_status:
            events = events.filter(status=event_status)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(CalendarEventSerializer(page, many=True).data)

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = CalendarEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            event = CalendarService.book_appointment(
                website_id=website_id,
                attendee_name=d["attendee_name"],
                attendee_phone=d["attendee_phone"],
                start_time=d["start_time"],
                end_time=d.get("end_time"),
                attendee_email=d.get("attendee_email", ""),
                title=d.get("title", ""),
                description=d.get("description", ""),
                assigned_to=request.user,
                tz=d.get("timezone", "UTC"),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CalendarEventSerializer(event).data, status=status.HTTP_201_CREATED)


class CalendarEventDetailView(APIView):
    """Get, update, or cancel a calendar event."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, event_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            event = CalendarEvent.objects.get(id=event_id, website_id=website_id)
        except CalendarEvent.DoesNotExist:
            return Response({"error": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CalendarEventSerializer(event).data)

    def put(self, request, website_id, event_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"error": "Status is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event = CalendarService.update_status(event_id, website_id, new_status)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CalendarEventSerializer(event).data)

    def delete(self, request, website_id, event_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            CalendarService.cancel_appointment(event_id, website_id)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailabilityView(APIView):
    """Check available appointment slots for a given date."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {"error": "date query parameter is required (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        date = parse_date(date_str)
        if not date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slots = CalendarService.get_available_slots(website_id=website_id, date=date)
        return Response({"date": date_str, "available_slots": slots})


# ── Callback Reminders ───────────────────────────────────────────────────────


class CallbackReminderListView(APIView):
    """List and create callback reminders."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        reminders = CallService.get_pending_reminders(website_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(reminders, request)
        return paginator.get_paginated_response(
            CallbackReminderSerializer(page, many=True).data
        )

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = CallbackReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        reminder = CallService.create_callback_reminder(
            website_id=website_id,
            contact_name=d["contact_name"],
            contact_phone=d["contact_phone"],
            remind_at=d["remind_at"],
            reason=d.get("reason", ""),
            assigned_to=request.user,
        )
        return Response(
            CallbackReminderSerializer(reminder).data, status=status.HTTP_201_CREATED
        )


class CallbackReminderDetailView(APIView):
    """Update or dismiss a callback reminder."""

    permission_classes = [IsAuthenticated]

    def put(self, request, website_id, reminder_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        action = request.data.get("action", "complete")
        notes = request.data.get("notes", "")

        if action == "dismiss":
            reminder = CallService.dismiss_reminder(reminder_id, website_id)
        else:
            reminder = CallService.complete_reminder(reminder_id, website_id, notes=notes)

        return Response(CallbackReminderSerializer(reminder).data)


# ── Todos / Action Items ─────────────────────────────────────────────────────


class TodoListView(APIView):
    """List todos extracted from calls, and get todo stats."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.voice_agent.services.extraction_service import ExtractionService

        todo_status = request.query_params.get("status")
        priority = request.query_params.get("priority")
        todos = ExtractionService.get_todos(website_id, status=todo_status, priority=priority)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(todos, request)
        return paginator.get_paginated_response(CallTodoSerializer(page, many=True).data)


class TodoDetailView(APIView):
    """Update a todo (status, priority, assignment)."""

    permission_classes = [IsAuthenticated]

    def put(self, request, website_id, todo_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.voice_agent.services.extraction_service import ExtractionService

        todo = ExtractionService.update_todo(
            todo_id=todo_id,
            website_id=website_id,
            status=request.data.get("status"),
            priority=request.data.get("priority"),
            due_date=request.data.get("due_date"),
            description=request.data.get("description"),
        )
        return Response(CallTodoSerializer(todo).data)


class TodoStatsView(APIView):
    """Get aggregate todo statistics."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.voice_agent.services.extraction_service import ExtractionService

        stats = ExtractionService.get_todo_stats(website_id)
        return Response(stats)


class CallExtractionView(APIView):
    """Get the AI extraction results for a specific call."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, call_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.voice_agent.models import CallExtraction

        try:
            extraction = CallExtraction.objects.get(call_log_id=call_id)
        except CallExtraction.DoesNotExist:
            return Response(
                {"error": "Extraction not yet available for this call."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CallExtractionSerializer(extraction).data)


# ── Retell AI Webhook ────────────────────────────────────────────────────────


class RetellWebhookView(APIView):
    """
    Webhook endpoint for Retell AI call events.

    Handles: call_started, call_ended, call_analyzed, tool_call
    No authentication required (webhook), verified by signature.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Verify webhook signature to prevent spoofed events
        if settings.RETELL_API_KEY:
            from apps.voice_agent.services.retell_service import RetellService

            signature = request.headers.get("X-Retell-Signature", "")
            if not signature or not RetellService.verify_webhook_signature(
                request.body, signature, settings.RETELL_API_KEY
            ):
                logger.warning("retell_webhook_invalid_signature")
                return Response(
                    {"error": "Invalid webhook signature."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        event = request.data.get("event", "")
        data = request.data.get("data", request.data)

        # Determine which website this call belongs to
        # Retell sends agent_id in the payload — look up the config
        agent_id = data.get("agent_id", "")
        call_data = data.get("call", {})
        if not agent_id:
            agent_id = call_data.get("agent_id", "")

        try:
            config = AgentConfig.objects.get(retell_agent_id=agent_id)
            website_id = config.website_id
        except AgentConfig.DoesNotExist:
            logger.warning("retell_webhook_unknown_agent", extra={"agent_id": agent_id})
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        if event == "call_started":
            CallService.process_call_started(website_id, data)

        elif event == "call_ended":
            CallService.process_call_ended(website_id, data)

        elif event == "call_analyzed":
            CallService.process_call_analyzed(website_id, data)

        elif event == "tool_call_invoked":
            return self._handle_tool_call(website_id, data, config)

        return Response({"status": "ok"})

    def _handle_tool_call(self, website_id, data, config):
        """Handle mid-call tool invocations (schedule, callback, availability)."""
        tool_name = data.get("tool_name", "")
        args = data.get("arguments", {})

        if tool_name == "schedule_appointment":
            return self._tool_schedule(website_id, args, config)
        elif tool_name == "request_callback":
            return self._tool_callback(website_id, args, data)
        elif tool_name == "check_availability":
            return self._tool_availability(website_id, args)

        return Response({"result": "Tool not recognized."})

    def _tool_schedule(self, website_id, args, config):
        """Handle the schedule_appointment tool call from the AI agent."""
        from django.utils.dateparse import parse_date as _parse_date

        date = _parse_date(args.get("preferred_date", ""))
        time_str = args.get("preferred_time", "")

        if not date or not time_str:
            return Response({"result": "I need both a date and time to schedule. Could you provide those?"})

        hour, minute = map(int, time_str.split(":"))
        from django.utils import timezone as tz

        start_time = tz.make_aware(
            datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
        )

        # Look up the call log for linking
        call_log = None
        external_call_id = args.get("call_id", "")
        if external_call_id:
            from apps.voice_agent.models import CallLog

            call_log = CallLog.objects.filter(external_call_id=external_call_id).first()

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
            # Trigger async calendar sync
            from apps.voice_agent.tasks import sync_calendar_event

            sync_calendar_event.delay(str(event.id))

            return Response({
                "result": (
                    f"Appointment booked for {args.get('attendee_name', '')} "
                    f"on {date.strftime('%B %d, %Y')} at {time_str}. "
                    f"Duration: {config.appointment_duration_minutes} minutes."
                )
            })
        except ValueError as e:
            return Response({"result": str(e)})

    def _tool_callback(self, website_id, args, data):
        """Handle the request_callback tool call."""
        from datetime import timedelta

        from django.utils import timezone as tz

        # Default to 1 hour from now if no time specified
        remind_at = tz.now() + timedelta(hours=1)
        preferred = args.get("preferred_time", "")
        if preferred:
            parsed = parse_datetime(preferred)
            if parsed:
                remind_at = parsed

        call_log = None
        external_call_id = data.get("call_id", "")
        if external_call_id:
            from apps.voice_agent.models import CallLog

            call_log = CallLog.objects.filter(external_call_id=external_call_id).first()

        reminder = CallService.create_callback_reminder(
            website_id=website_id,
            contact_name=args.get("contact_name", ""),
            contact_phone=args.get("contact_phone", ""),
            remind_at=remind_at,
            reason=args.get("reason", ""),
            call_log=call_log,
        )

        # Trigger notification
        from apps.voice_agent.tasks import send_callback_notification

        send_callback_notification.delay(str(reminder.id))

        return Response({
            "result": (
                f"Callback reminder set for {args.get('contact_name', '')}. "
                f"Someone will call you back."
            )
        })

    def _tool_availability(self, website_id, args):
        """Handle the check_availability tool call."""
        date = parse_date(args.get("date", ""))
        if not date:
            return Response({"result": "I need a valid date to check availability."})

        slots = CalendarService.get_available_slots(website_id=website_id, date=date)
        if not slots:
            return Response({
                "result": f"No available slots on {date.strftime('%B %d, %Y')}. Would you like to try another date?"
            })

        slot_list = ", ".join(f"{s['start']}-{s['end']}" for s in slots[:6])
        more = f" and {len(slots) - 6} more" if len(slots) > 6 else ""
        return Response({
            "result": f"Available slots on {date.strftime('%B %d, %Y')}: {slot_list}{more}"
        })


# ── Phone Numbers ─────────────────────────────────────────────────────────────


class PhoneNumberListView(APIView):
    """List and add work phone numbers for a website."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        numbers = PhoneNumber.objects.filter(website=website)
        return Response(PhoneNumberSerializer(numbers, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = PhoneNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(website=website)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PhoneNumberDetailView(APIView):
    """Update or delete a phone number."""

    permission_classes = [IsAuthenticated]

    def _get_number(self, request, website_id, number_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        return PhoneNumber.objects.get(id=number_id, website=website)

    def put(self, request, website_id, number_id):
        number = self._get_number(request, website_id, number_id)
        serializer = PhoneNumberSerializer(number, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, website_id, number_id):
        number = self._get_number(request, website_id, number_id)
        number.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Agent Context Documents ───────────────────────────────────────────────────


class AgentContextDocumentListView(APIView):
    """List and create agent knowledge-base documents."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        docs = AgentContextDocument.objects.filter(website=website)
        return Response(AgentContextDocumentSerializer(docs, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = AgentContextDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(website=website)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AgentContextDocumentDetailView(APIView):
    """Update or delete a context document."""

    permission_classes = [IsAuthenticated]

    def _get_doc(self, request, website_id, doc_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        return AgentContextDocument.objects.get(id=doc_id, website=website)

    def put(self, request, website_id, doc_id):
        doc = self._get_doc(request, website_id, doc_id)
        serializer = AgentContextDocumentSerializer(doc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, website_id, doc_id):
        doc = self._get_doc(request, website_id, doc_id)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
