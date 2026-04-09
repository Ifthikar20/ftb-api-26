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
    CallCampaignSerializer,
    CallExtractionSerializer,
    CallLogSerializer,
    CallTargetSerializer,
    CallTodoSerializer,
    PhoneNumberSerializer,
)
from apps.voice_agent.models import (
    AgentConfig,
    AgentContextDocument,
    CalendarEvent,
    CallCampaign,
    CallTarget,
    PhoneNumber,
)
from apps.voice_agent.services.calendar_service import CalendarService
from apps.voice_agent.services.call_service import CallService
from apps.voice_agent.services.prompt_builder import build_retell_system_prompt
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination
from core.views import TenantScopedAPIView

logger = logging.getLogger("apps")


# ── Agent Configuration ──────────────────────────────────────────────────────


def _sync_prompt_to_retell(config: AgentConfig) -> str:
    """Push the merged system prompt to Retell. Returns 'ok', 'skipped', or 'failed'.

    Never raises — callers can surface the status to the UI but DB writes
    must succeed even if Retell is unreachable.
    """
    if not (config.retell_agent_id and config.is_active):
        return "skipped"
    try:
        from apps.voice_agent.services.retell_service import RetellService

        RetellService.update_agent(
            config.retell_agent_id,
            general_prompt=build_retell_system_prompt(config),
        )
        return "ok"
    except Exception as e:
        logger.warning(
            "retell_prompt_sync_failed",
            extra={"agent_id": config.retell_agent_id, "error": str(e)},
        )
        return "failed"


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

        # If agent exists in Retell, update it with the merged KB prompt
        if config.retell_agent_id and config.is_active:
            try:
                from apps.voice_agent.services.retell_service import RetellService

                RetellService.update_agent(
                    config.retell_agent_id,
                    general_prompt=build_retell_system_prompt(config),
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
    """Deprecated: the voice agent is always-on per website.

    Retained so older clients calling ``/activate/`` keep working — it now
    simply ensures an AgentConfig row exists with ``is_active=True`` and
    returns it. Deactivation is no longer supported from the UI.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = AgentConfig.objects.get_or_create(
            website=website, defaults={"business_hours": {}}
        )
        if not config.is_active:
            config.is_active = True
            config.save(update_fields=["is_active", "updated_at"])
        return Response(AgentConfigSerializer(config).data)


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
        """Handle mid-call tool invocations (schedule, callback, availability).

        Delegates to ``services.tool_handlers`` so the LiveKit worker can reuse
        the same logic.
        """
        from apps.voice_agent.services import tool_handlers

        tool_name = data.get("tool_name", "")
        args = data.get("arguments", {})
        external_call_id = data.get("call_id", "") or args.get("call_id", "")

        if tool_name == "schedule_appointment":
            return Response(
                tool_handlers.schedule_appointment(website_id, args, external_call_id)
            )
        elif tool_name == "request_callback":
            return Response(
                tool_handlers.request_callback(website_id, args, external_call_id)
            )
        elif tool_name == "check_availability":
            return Response(tool_handlers.check_availability(website_id, args))

        return Response({"result": "Tool not recognized."})

# ── Phone Numbers ─────────────────────────────────────────────────────────────


class PhoneNumberListView(TenantScopedAPIView):
    """List and add work phone numbers for a website."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        numbers = PhoneNumber.objects.filter(website=website)
        return Response(PhoneNumberSerializer(numbers, many=True).data)

    def post(self, request, website_id):
        website = self.get_website(website_id)
        serializer = PhoneNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # MFA gate: callers must have completed an SMS/call verification for
        # this exact number before we'll attach it to the website. The
        # frontend posts ``verification_id`` from the confirm step.
        from apps.voice_agent.services import phone_verification_service as pvs

        verification_id = request.data.get("verification_id")
        verification = pvs.consume(
            website=website,
            verification_id=verification_id,
            number=serializer.validated_data.get("number", ""),
        )
        if not verification:
            return Response(
                {
                    "error": (
                        "Phone number must be verified via SMS or call before "
                        "it can be added. Start a verification first."
                    ),
                    "code": "verification_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone as _tz
        instance = serializer.save(
            website=website, is_verified=True, verified_at=_tz.now()
        )
        return Response(PhoneNumberSerializer(instance).data, status=status.HTTP_201_CREATED)


class PhoneNumberVerifyStartView(TenantScopedAPIView):
    """Step 1 of phone-number MFA: send a code via SMS or voice call."""

    def post(self, request, website_id):
        website = self.get_website(website_id)
        from apps.voice_agent.services import phone_verification_service as pvs
        try:
            verification = pvs.start(
                website=website,
                number=(request.data.get("number") or "").strip(),
                channel=request.data.get("channel") or "sms",
                requested_by=request.user,
            )
        except pvs.PhoneVerificationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "verification_id": str(verification.id),
                "channel": verification.channel,
                "expires_at": verification.expires_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class PhoneNumberVerifyConfirmView(TenantScopedAPIView):
    """Step 2 of phone-number MFA: confirm the code the user received."""

    def post(self, request, website_id):
        website = self.get_website(website_id)
        from apps.voice_agent.services import phone_verification_service as pvs
        try:
            verification = pvs.confirm(
                website=website,
                verification_id=request.data.get("verification_id") or "",
                code=(request.data.get("code") or "").strip(),
            )
        except pvs.PhoneVerificationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "verification_id": str(verification.id),
                "number": verification.number,
                "verified": True,
            }
        )


class PhoneNumberDetailView(TenantScopedAPIView):
    """Update or delete a phone number."""

    def _get_number(self, website_id, number_id):
        website = self.get_website(website_id)
        return self.get_tenant_object(PhoneNumber.objects.all(), id=number_id, website=website)

    def put(self, request, website_id, number_id):
        number = self._get_number(website_id, number_id)
        serializer = PhoneNumberSerializer(number, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, website_id, number_id):
        number = self._get_number(website_id, number_id)
        number.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Agent Context Documents ───────────────────────────────────────────────────


UPLOAD_MAX_BYTES = 100 * 1024  # 100 KB
UPLOAD_ALLOWED_EXTS = (".md", ".markdown", ".txt")


def _config_for_website(website):
    """Return the AgentConfig for a website if one exists, else None."""
    return AgentConfig.objects.filter(website=website).first()


class AgentContextDocumentListView(APIView):
    """List, create, and upload agent knowledge-base documents."""

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
        retell_sync = "skipped"
        config = _config_for_website(website)
        if config:
            retell_sync = _sync_prompt_to_retell(config)
        return Response(
            {**serializer.data, "retell_sync": retell_sync},
            status=status.HTTP_201_CREATED,
        )


class AgentContextDocumentUploadView(APIView):
    """Upload a markdown file as a new knowledge-base document."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)

        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"error": "Missing 'file' in multipart upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = (upload.name or "").lower()
        if not name.endswith(UPLOAD_ALLOWED_EXTS):
            return Response(
                {"error": "Only .md, .markdown, or .txt files are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload.size > UPLOAD_MAX_BYTES:
            return Response(
                {"error": f"File too large. Max {UPLOAD_MAX_BYTES // 1024} KB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = upload.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"error": "File must be UTF-8 encoded text."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = (request.data.get("title") or "").strip()
        if not title:
            # Strip extension from filename to use as title
            base = upload.name.rsplit(".", 1)[0]
            title = base.replace("_", " ").replace("-", " ").strip() or "Untitled"

        doc = AgentContextDocument.objects.create(
            website=website,
            title=title[:200],
            content=content,
            is_active=True,
        )

        retell_sync = "skipped"
        config = _config_for_website(website)
        if config:
            retell_sync = _sync_prompt_to_retell(config)

        return Response(
            {**AgentContextDocumentSerializer(doc).data, "retell_sync": retell_sync},
            status=status.HTTP_201_CREATED,
        )


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
        retell_sync = "skipped"
        config = _config_for_website(doc.website)
        if config:
            retell_sync = _sync_prompt_to_retell(config)
        return Response({**serializer.data, "retell_sync": retell_sync})

    def delete(self, request, website_id, doc_id):
        doc = self._get_doc(request, website_id, doc_id)
        website = doc.website
        doc.delete()
        config = _config_for_website(website)
        if config:
            _sync_prompt_to_retell(config)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Outbound Calling: Campaigns + Call Now ────────────────────────────────────


def _ensure_website(request, website_id):
    return WebsiteService.get_for_user(user=request.user, website_id=website_id)


class CallCampaignListView(APIView):
    """List or create outbound call campaigns for a website."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request, website_id):
        website = _ensure_website(request, website_id)
        qs = CallCampaign.objects.filter(website=website).order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            CallCampaignSerializer(page, many=True).data
        )

    def post(self, request, website_id):
        website = _ensure_website(request, website_id)
        serializer = CallCampaignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from_number = serializer.validated_data["from_number"]
        if from_number.website_id != website.id:
            return Response(
                {"detail": "from_number does not belong to this website"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign = serializer.save(website=website, created_by=request.user)
        return Response(
            CallCampaignSerializer(campaign).data, status=status.HTTP_201_CREATED
        )


class CallCampaignDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, website_id, campaign_id):
        website = _ensure_website(request, website_id)
        return CallCampaign.objects.get(id=campaign_id, website=website)

    def get(self, request, website_id, campaign_id):
        try:
            campaign = self._get(request, website_id, campaign_id)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(CallCampaignSerializer(campaign).data)

    def put(self, request, website_id, campaign_id):
        try:
            campaign = self._get(request, website_id, campaign_id)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if campaign.status == CallCampaign.STATUS_RUNNING:
            return Response(
                {"detail": "pause the campaign before editing"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CallCampaignSerializer(campaign, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        from_number = serializer.validated_data.get("from_number", campaign.from_number)
        if from_number.website_id != campaign.website_id:
            return Response(
                {"detail": "from_number does not belong to this website"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(CallCampaignSerializer(campaign).data)

    def delete(self, request, website_id, campaign_id):
        try:
            campaign = self._get(request, website_id, campaign_id)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CallTargetListView(APIView):
    """List or add targets to a campaign."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def _campaign(self, request, website_id, campaign_id):
        website = _ensure_website(request, website_id)
        return CallCampaign.objects.get(id=campaign_id, website=website)

    def get(self, request, website_id, campaign_id):
        try:
            campaign = self._campaign(request, website_id, campaign_id)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        qs = campaign.targets.all().order_by("created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            CallTargetSerializer(page, many=True).data
        )

    def post(self, request, website_id, campaign_id):
        try:
            campaign = self._campaign(request, website_id, campaign_id)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CallTargetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target, _ = CallTarget.objects.get_or_create(
            campaign=campaign,
            phone=serializer.validated_data["phone"],
            defaults={
                "name": serializer.validated_data.get("name", ""),
                "metadata": serializer.validated_data.get("metadata", {}),
                "max_attempts": serializer.validated_data.get("max_attempts", 2),
            },
        )
        return Response(
            CallTargetSerializer(target).data, status=status.HTTP_201_CREATED
        )


class CallTargetCSVUploadView(APIView):
    """Bulk-upload targets via CSV. First row must contain a ``phone`` column;
    optional ``name`` column. Any other columns become per-target ``metadata``."""

    permission_classes = [IsAuthenticated]

    MAX_BYTES = 5 * 1024 * 1024  # 5 MB

    def post(self, request, website_id, campaign_id):
        import csv
        import io

        website = _ensure_website(request, website_id)
        try:
            campaign = CallCampaign.objects.get(id=campaign_id, website=website)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if upload.size > self.MAX_BYTES:
            return Response(
                {"detail": "file too large (max 5MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            text = upload.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"detail": "file must be UTF-8 encoded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "phone" not in reader.fieldnames:
            return Response(
                {"detail": "CSV must have a 'phone' column"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        skipped = 0
        for row in reader:
            phone = (row.get("phone") or "").strip()
            if not phone:
                skipped += 1
                continue
            name = (row.get("name") or "").strip()
            metadata = {
                k: v for k, v in row.items() if k not in ("phone", "name") and v
            }
            _, was_created = CallTarget.objects.get_or_create(
                campaign=campaign,
                phone=phone,
                defaults={"name": name, "metadata": metadata},
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        return Response(
            {"created": created, "skipped": skipped},
            status=status.HTTP_201_CREATED,
        )


class CampaignStartView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "voice_outbound"

    def post(self, request, website_id, campaign_id):
        from apps.voice_agent.tasks import dispatch_campaign

        website = _ensure_website(request, website_id)
        try:
            campaign = CallCampaign.objects.get(id=campaign_id, website=website)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not campaign.from_number.livekit_outbound_trunk_id:
            return Response(
                {"detail": "from_number not provisioned with LiveKit outbound trunk"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not campaign.targets.filter(status=CallTarget.STATUS_PENDING).exists():
            return Response(
                {"detail": "no pending targets to dial"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.status = CallCampaign.STATUS_RUNNING
        campaign.save(update_fields=["status", "updated_at"])
        dispatch_campaign.delay(str(campaign.id))
        return Response(CallCampaignSerializer(campaign).data)


class CampaignPauseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, campaign_id):
        website = _ensure_website(request, website_id)
        try:
            campaign = CallCampaign.objects.get(id=campaign_id, website=website)
        except CallCampaign.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        campaign.status = CallCampaign.STATUS_PAUSED
        campaign.save(update_fields=["status", "updated_at"])
        return Response(CallCampaignSerializer(campaign).data)


class CallNowView(APIView):
    """Place a single ad-hoc outbound call. Creates a one-target campaign and
    immediately dispatches the dialer."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "voice_outbound"

    def post(self, request, website_id):
        from apps.voice_agent.tasks import place_outbound_call

        website = _ensure_website(request, website_id)
        phone = (request.data.get("phone") or "").strip()
        if not phone:
            return Response(
                {"detail": "phone is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        from_number_id = request.data.get("from_number_id")
        if not from_number_id:
            return Response(
                {"detail": "from_number_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from_number = PhoneNumber.objects.get(id=from_number_id, website=website)
        except PhoneNumber.DoesNotExist:
            return Response(
                {"detail": "from_number not found for this website"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not from_number.livekit_outbound_trunk_id:
            return Response(
                {"detail": "from_number not provisioned with LiveKit outbound trunk"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        welcome = request.data.get("welcome_override") or ""
        if not welcome:
            config = AgentConfig.objects.filter(website=website).first()
            welcome = (config.greeting_message if config else "") or "Hello!"

        campaign = CallCampaign.objects.create(
            website=website,
            name=f"Ad-hoc call to {phone}",
            welcome_message=welcome,
            from_number=from_number,
            status=CallCampaign.STATUS_RUNNING,
            max_concurrent_calls=1,
            calls_per_minute=1,
            respect_business_hours=False,
            created_by=request.user,
        )
        target = CallTarget.objects.create(
            campaign=campaign,
            phone=phone,
            name=request.data.get("name", ""),
            max_attempts=1,
        )
        place_outbound_call.delay(str(target.id))
        return Response(
            {
                "campaign_id": str(campaign.id),
                "target_id": str(target.id),
                "status": "dialing",
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ── Onboarding: templates + setup status ─────────────────────────────────────


class OnboardingTemplateListView(APIView):
    """List the starter knowledge-base templates the UI offers as one-click adds.

    Optional query param: ``?segment=inbound|outbound`` to filter.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.voice_agent.services import onboarding

        segment = request.query_params.get("segment")
        try:
            templates = onboarding.list_templates(segment)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            [
                {
                    "slug": t.slug,
                    "title": t.title,
                    "description": t.description,
                    "segment": t.segment,
                    "sort_order": t.sort_order,
                    "recommended": t.recommended,
                }
                for t in templates
            ]
        )


class OnboardingTemplatePreviewView(APIView):
    """Return the rendered markdown for a template (with business_name substituted)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, slug):
        from apps.voice_agent.services import onboarding

        website = _ensure_website(request, website_id)
        try:
            template = onboarding.get_template(slug)
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        config = AgentConfig.objects.filter(website=website).first()
        business_name = (config.business_name if config else "") or ""
        return Response(
            {
                "slug": template.slug,
                "title": template.title,
                "segment": template.segment,
                "content": onboarding.render_template(slug, business_name=business_name),
            }
        )


class OnboardingTemplateApplyView(APIView):
    """Create (or update) an AgentContextDocument from a starter template."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, slug):
        from apps.voice_agent.services import onboarding

        website = _ensure_website(request, website_id)
        try:
            doc = onboarding.apply_template(website=website, slug=slug)
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Trigger Retell prompt sync if the agent is already live.
        config = AgentConfig.objects.filter(website=website).first()
        if config:
            _sync_prompt_to_retell(config)

        return Response(
            AgentContextDocumentSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )


class OnboardingSetupStatusView(APIView):
    """Per-website checklist for the inbound + outbound onboarding flows.

    Used by the UI to render two progress cards ("AI Receptionist" and
    "AI Sales Caller") with step-by-step CTAs.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        from apps.voice_agent.services import onboarding

        website = _ensure_website(request, website_id)
        return Response(onboarding.setup_status(website))


# ── Internal endpoints used by the LiveKit agent worker ──────────────────────


def _check_internal_token(request) -> bool:
    expected = getattr(settings, "LIVEKIT_AGENT_API_TOKEN", "")
    if not expected:
        return False
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {expected}"


class InternalAgentBootstrapView(APIView):
    """Called by the LiveKit worker when it joins a room. Returns the merged
    KB-aware system prompt + agent settings for a website."""

    permission_classes = [AllowAny]

    def get(self, request):
        if not _check_internal_token(request):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        website_id = request.query_params.get("website_id")
        if not website_id:
            return Response(
                {"detail": "website_id required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            config = AgentConfig.objects.select_related("website").get(
                website_id=website_id
            )
        except AgentConfig.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "website_id": str(config.website_id),
                "system_prompt": build_retell_system_prompt(config),
                "greeting": config.greeting_message,
                "business_name": config.business_name,
                "timezone": config.timezone,
                "tools": ["schedule_appointment", "request_callback", "check_availability"],
            }
        )


class InternalCallFinishView(APIView):
    """Called by the LiveKit worker when an outbound call ends. Stores the
    transcript on the CallLog and queues post-call extraction."""

    permission_classes = [AllowAny]

    def post(self, request):
        from django.utils import timezone as tz

        from apps.voice_agent.models import CallLog
        from apps.voice_agent.tasks import extract_call_data

        if not _check_internal_token(request):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        call_log_id = request.data.get("call_log_id")
        if not call_log_id:
            return Response(
                {"detail": "call_log_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            call_log = CallLog.objects.select_related("target").get(id=call_log_id)
        except CallLog.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        transcript = request.data.get("transcript", "") or ""
        duration = int(request.data.get("duration", 0) or 0)
        ended_reason = (request.data.get("ended_reason") or "").lower()

        call_log.transcript = transcript
        call_log.duration_seconds = duration
        call_log.ended_at = tz.now()
        if ended_reason in ("no_answer", "noanswer"):
            call_log.status = CallLog.STATUS_MISSED
            target_status = CallTarget.STATUS_NO_ANSWER
        elif ended_reason in ("busy",):
            call_log.status = CallLog.STATUS_FAILED
            target_status = CallTarget.STATUS_BUSY
        elif ended_reason in ("failed", "error"):
            call_log.status = CallLog.STATUS_FAILED
            target_status = CallTarget.STATUS_FAILED
        else:
            call_log.status = CallLog.STATUS_COMPLETED
            target_status = CallTarget.STATUS_COMPLETED
        call_log.save(
            update_fields=[
                "transcript", "duration_seconds", "ended_at", "status", "updated_at",
            ]
        )

        if call_log.target_id:
            target = call_log.target
            target.status = target_status
            target.save(update_fields=["status", "updated_at"])

        try:
            extract_call_data.delay(str(call_log.id))
        except Exception:  # noqa: BLE001
            logger.exception(
                "extract_call_data_dispatch_failed",
                extra={"call_log_id": str(call_log.id)},
            )

        return Response({"status": "ok"})
