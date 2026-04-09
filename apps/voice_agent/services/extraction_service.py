"""
Post-call extraction service.

Runs after every completed call to extract structured data:
- Caller info (name, phone, email, company)
- Call summary and category
- Action items / todos
- Follow-up requirements
- Appointment details
- Sentiment analysis

Uses the self-hosted LLM with guided JSON decoding for guaranteed valid output.
"""

import json
import logging
import time

from django.utils import timezone

logger = logging.getLogger("apps")

# JSON schema for guided decoding — vLLM guarantees output matches this exactly
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "caller_info": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "company": {"type": "string"},
            },
            "required": ["name", "phone"],
        },
        "call_summary": {"type": "string"},
        "call_category": {
            "type": "string",
            "enum": ["appointment", "inquiry", "complaint", "support", "sales", "other"],
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "negative", "frustrated"],
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "assigned_to": {
                        "type": "string",
                        "enum": ["caller", "business", "unclear"],
                    },
                    "due_date": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["description", "priority"],
            },
        },
        "appointments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "description": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["date", "time", "description"],
            },
        },
        "follow_ups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "urgency": {
                        "type": "string",
                        "enum": ["immediate", "within_24h", "this_week", "no_rush"],
                    },
                },
                "required": ["description", "urgency"],
            },
        },
    },
    "required": [
        "caller_info",
        "call_summary",
        "call_category",
        "sentiment",
        "action_items",
    ],
}

EXTRACTION_PROMPT = """You are an expert at extracting structured information from phone call transcripts.

Analyze the following transcript and extract ALL relevant data into the specified JSON format.

Rules:
- Extract the caller's name, phone, email, and company if mentioned.
- Write a concise 1-2 sentence call summary.
- Categorize the call: appointment, inquiry, complaint, support, sales, or other.
- List ALL action items that need follow-up. Each must have a description and priority.
- If appointments were discussed, include date, time, and whether confirmed.
- Identify any follow-ups needed with their urgency level.
- Assess the caller's sentiment: positive, neutral, negative, or frustrated.
- If information was not mentioned, use empty strings. Do not guess.

TRANSCRIPT:
{transcript}

Extract the structured data now."""


class ExtractionService:
    """Extract structured data and todos from call transcripts."""

    @staticmethod
    def extract_from_transcript(call_log):
        """
        Run post-call extraction on a completed call.
        Creates CallExtraction and CallTodo records.

        Uses the self-hosted LLM with guided JSON decoding.
        Falls back to basic parsing if the LLM is unavailable.
        """
        from apps.voice_agent.models import CallExtraction, CallTodo

        if not call_log.transcript:
            logger.info("extraction_skipped_no_transcript", extra={"call_id": str(call_log.id)})
            return None

        start = time.monotonic()

        prompt = EXTRACTION_PROMPT.format(transcript=call_log.transcript)

        # Try self-hosted LLM first
        extracted = None
        model_used = ""

        try:
            from apps.voice_agent.services.selfhosted_inference import SelfHostedLLM

            result = SelfHostedLLM.extract_json(prompt, EXTRACTION_SCHEMA)
            extracted = result["data"]
            model_used = result["model"]
        except Exception as e:
            logger.warning("selfhosted_extraction_failed", extra={"error": str(e)})

        # Fallback: try OpenAI API if self-hosted is down
        if not extracted:
            try:
                extracted = ExtractionService._fallback_openai_extract(prompt)
                model_used = "gpt-4o-mini (fallback)"
            except Exception as e:
                logger.warning("fallback_extraction_failed", extra={"error": str(e)})
                return None

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Save extraction record
        extraction, _ = CallExtraction.objects.update_or_create(
            call_log=call_log,
            defaults={
                "caller_info": extracted.get("caller_info", {}),
                "call_summary": extracted.get("call_summary", ""),
                "call_category": extracted.get("call_category", "other"),
                "sentiment": extracted.get("sentiment", ""),
                "follow_ups": extracted.get("follow_ups", []),
                "appointments_detected": extracted.get("appointments", []),
                "raw_llm_output": extracted,
                "model_used": model_used,
                "processing_time_ms": elapsed_ms,
            },
        )

        # Update the call log with extracted caller info
        caller = extracted.get("caller_info", {})
        update_fields = []
        if caller.get("name") and not call_log.caller_name:
            call_log.caller_name = caller["name"]
            update_fields.append("caller_name")
        if caller.get("email") and not call_log.caller_email:
            call_log.caller_email = caller["email"]
            update_fields.append("caller_email")
        if caller.get("company") and not call_log.caller_company:
            call_log.caller_company = caller["company"]
            update_fields.append("caller_company")
        if extracted.get("call_summary") and not call_log.summary:
            call_log.summary = extracted["call_summary"]
            update_fields.append("summary")
        if extracted.get("sentiment") and not call_log.sentiment:
            call_log.sentiment = extracted["sentiment"]
            update_fields.append("sentiment")
        if extracted.get("call_category") and not call_log.call_intent:
            call_log.call_intent = extracted["call_category"]
            update_fields.append("call_intent")

        if update_fields:
            call_log.save(update_fields=update_fields + ["updated_at"])

        # Create todo items from action items
        action_items = extracted.get("action_items", [])
        todos_created = []
        for item in action_items:
            if not item.get("description"):
                continue
            todo = CallTodo.objects.create(
                website_id=call_log.website_id,
                call_log=call_log,
                description=item["description"],
                priority=item.get("priority", "medium"),
                due_date=ExtractionService._parse_due_date(item.get("due_date", "")),
            )
            todos_created.append(todo)

        # Create todos from follow-ups too
        for fu in extracted.get("follow_ups", []):
            if not fu.get("description"):
                continue
            priority = "high" if fu.get("urgency") == "immediate" else "medium"
            if fu.get("urgency") == "no_rush":
                priority = "low"
            todo = CallTodo.objects.create(
                website_id=call_log.website_id,
                call_log=call_log,
                description=f"Follow-up: {fu['description']}",
                priority=priority,
            )
            todos_created.append(todo)

        logger.info(
            "extraction_completed",
            extra={
                "call_id": str(call_log.id),
                "model": model_used,
                "todos_created": len(todos_created),
                "latency_ms": elapsed_ms,
                "category": extracted.get("call_category"),
            },
        )

        # Lead detection: turn the freshly-extracted data into a lead score.
        # Done synchronously here so the call log is consistent the moment
        # extraction returns. Failures are logged but don't break extraction.
        try:
            from apps.voice_agent.services.lead_scoring_service import score_call

            score_call(call_log, extraction_data={
                "caller_info": extracted.get("caller_info", {}),
                "call_summary": extracted.get("call_summary", ""),
                "call_category": extracted.get("call_category", ""),
                "sentiment": extracted.get("sentiment", ""),
                "follow_ups": extracted.get("follow_ups", []),
                "appointments_detected": extracted.get("appointments", []),
            })
        except Exception:  # noqa: BLE001
            logger.exception(
                "lead_scoring_failed",
                extra={"call_id": str(call_log.id)},
            )

        return extraction

    @staticmethod
    def _parse_due_date(date_str):
        """Try to parse a due date string. Returns None if unparseable."""
        if not date_str:
            return None
        from django.utils.dateparse import parse_date

        return parse_date(date_str)

    @staticmethod
    def _fallback_openai_extract(prompt):
        """Fallback to OpenAI API if self-hosted LLM is unavailable."""
        from django.conf import settings as s

        if not s.OPENAI_API_KEY:
            raise RuntimeError("No OpenAI API key configured for fallback.")

        import openai

        client = openai.OpenAI(api_key=s.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )
        content = resp.choices[0].message.content
        return json.loads(content)

    @staticmethod
    def get_todos(website_id, *, status=None, priority=None):
        """Get todos for a website with optional filters."""
        from apps.voice_agent.models import CallTodo

        qs = CallTodo.objects.filter(website_id=website_id).select_related("call_log", "assigned_to")
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        return qs

    @staticmethod
    def update_todo(todo_id, website_id, **kwargs):
        """Update a todo's status, assignment, etc."""
        from apps.voice_agent.models import CallTodo

        try:
            todo = CallTodo.objects.get(id=todo_id, website_id=website_id)
        except CallTodo.DoesNotExist:
            from core.exceptions import ResourceNotFound
            raise ResourceNotFound("Todo not found.") from None

        allowed_fields = {"status", "priority", "assigned_to", "due_date", "description"}
        update_fields = []
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(todo, field, value)
                update_fields.append(field)

        if "status" in kwargs and kwargs["status"] == "done":
            todo.completed_at = timezone.now()
            update_fields.append("completed_at")

        if update_fields:
            todo.save(update_fields=update_fields + ["updated_at"])

        return todo

    @staticmethod
    def get_todo_stats(website_id):
        """Get todo statistics."""
        from django.db.models import Count, Q

        from apps.voice_agent.models import CallTodo

        qs = CallTodo.objects.filter(website_id=website_id)
        return qs.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(status="open")),
            in_progress=Count("id", filter=Q(status="in_progress")),
            done=Count("id", filter=Q(status="done")),
            high_priority=Count("id", filter=Q(priority="high", status__in=["open", "in_progress"])),
        )
