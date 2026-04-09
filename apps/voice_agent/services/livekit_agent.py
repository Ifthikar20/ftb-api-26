"""
LiveKit Voice Agent — multi-provider voice pipeline.

Architecture:
  Phone Call -> Telnyx SIP -> LiveKit Server -> This Agent
                                                   |
                                        STT (Groq Whisper / Self-hosted Whisper)
                                                   |
                                        LLM (Groq Llama / Self-hosted vLLM)
                                                   |
                                        TTS (Edge-TTS / Self-hosted Kokoro)
                                                   |
                                           Audio back to caller

Provider Modes (set VOICE_PROVIDER_MODE env var):
  "groq"       — Groq Whisper + Groq Llama 3.1 + Edge-TTS  ($0/min — free tier)
  "selfhosted" — Faster-Whisper + vLLM + Kokoro             ($0/min — own GPU)
  "openai"     — Deepgram + GPT-4o-mini + OpenAI TTS        (~$0.01/min — API)

Requirements:
  pip install livekit-agents livekit-plugins-openai livekit-plugins-silero

To run:
  VOICE_PROVIDER_MODE=groq GROQ_API_KEY=gsk_... \\
  python -m apps.voice_agent.services.livekit_agent
"""

import logging
import os

logger = logging.getLogger("apps")

# Only import LiveKit when actually running the agent
# (prevents import errors when the app is loaded but LiveKit isn't installed yet)
LIVEKIT_AVAILABLE = False
try:
    from livekit.agents import (
        AutoSubscribe,
        JobContext,
        WorkerOptions,
        cli,
    )
    from livekit.agents.voice import VoiceSession
    from livekit.plugins import openai, silero

    # Optional plugins — only needed for specific provider modes
    try:
        from livekit.plugins import deepgram
    except ImportError:
        deepgram = None

    # ChatContext is the canonical way to seed the LLM with a system prompt
    # in livekit-agents 0.x. Newer SDKs (1.x) accept ``instructions=`` on
    # the Agent class instead — we try both at session-create time so this
    # file works across SDK versions without a hard pin.
    try:
        from livekit.agents.llm import ChatContext  # type: ignore
    except ImportError:
        ChatContext = None  # type: ignore

    LIVEKIT_AVAILABLE = True
except ImportError:
    ChatContext = None  # type: ignore
    pass


# ── Tool Definitions for the LLM ────────────────────────────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "schedule_appointment",
            "description": (
                "Schedule an appointment for the caller. "
                "Use this when the caller wants to book a meeting or appointment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "attendee_name": {"type": "string", "description": "Full name of the person"},
                    "attendee_phone": {"type": "string", "description": "Phone number"},
                    "attendee_email": {"type": "string", "description": "Email address (optional)"},
                    "preferred_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "preferred_time": {"type": "string", "description": "Time in HH:MM format (24h)"},
                    "reason": {"type": "string", "description": "Reason for the appointment"},
                },
                "required": ["attendee_name", "preferred_date", "preferred_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_callback",
            "description": "Set a callback reminder when the caller wants to be called back later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string", "description": "Name of the person"},
                    "contact_phone": {"type": "string", "description": "Phone number to call back"},
                    "preferred_time": {"type": "string", "description": "When to call back"},
                    "reason": {"type": "string", "description": "Reason for callback"},
                },
                "required": ["contact_name", "contact_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available appointment slots for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                },
                "required": ["date"],
            },
        },
    },
]


def _get_django_api_base():
    """Get the Django API base URL for tool callbacks."""
    return os.environ.get("DJANGO_API_BASE", "http://localhost:8000/api/v1")


def _parse_room_metadata(metadata):
    """Parse the JSON metadata LiveKit attaches to a room.

    Outbound calls dispatched by ``tasks.place_outbound_call`` include:
      ``website_id``, ``campaign_id``, ``target_id``, ``call_log_id``,
      ``welcome``, ``recipient_name``.
    Inbound calls only carry ``website_id``.
    """
    import json

    try:
        if isinstance(metadata, str):
            return json.loads(metadata) if metadata else {}
        return metadata or {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_website_id_from_metadata(metadata):
    """Extract website_id from room metadata (back-compat helper)."""
    return _parse_room_metadata(metadata).get("website_id", "")


async def _handle_tool_call(tool_name, arguments, website_id):
    """
    Execute a tool call by hitting the Django API.
    This runs during the call to schedule appointments, check availability, etc.
    """
    import httpx

    base = _get_django_api_base()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('LIVEKIT_AGENT_API_TOKEN', '')}",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        if tool_name == "schedule_appointment":
            resp = await client.post(
                f"{base}/voice-agent/{website_id}/calendar/",
                json={
                    "attendee_name": arguments.get("attendee_name", ""),
                    "attendee_phone": arguments.get("attendee_phone", ""),
                    "attendee_email": arguments.get("attendee_email", ""),
                    "title": f"Appointment: {arguments.get('reason', '')}".strip(": "),
                    "start_time": f"{arguments['preferred_date']}T{arguments['preferred_time']}:00Z",
                },
                headers=headers,
            )
            if resp.status_code == 201:
                return (
                    f"Appointment booked for {arguments.get('attendee_name', '')} "
                    f"on {arguments['preferred_date']} at {arguments['preferred_time']}."
                )
            error = resp.json().get("error", "Could not book appointment.")
            return f"Booking failed: {error}"

        elif tool_name == "check_availability":
            resp = await client.get(
                f"{base}/voice-agent/{website_id}/calendar/availability/",
                params={"date": arguments["date"]},
                headers=headers,
            )
            data = resp.json()
            slots = data.get("data", {}).get("available_slots", data.get("available_slots", []))
            if not slots:
                return f"No available slots on {arguments['date']}. Try another date."
            slot_list = ", ".join(f"{s['start']}-{s['end']}" for s in slots[:6])
            return f"Available slots on {arguments['date']}: {slot_list}"

        elif tool_name == "request_callback":
            resp = await client.post(
                f"{base}/voice-agent/{website_id}/reminders/",
                json={
                    "contact_name": arguments.get("contact_name", ""),
                    "contact_phone": arguments.get("contact_phone", ""),
                    "remind_at": arguments.get("preferred_time", ""),
                    "reason": arguments.get("reason", ""),
                },
                headers=headers,
            )
            if resp.status_code == 201:
                return f"Callback reminder set for {arguments.get('contact_name', '')}."
            return "Could not set callback reminder."

    return "Tool not recognized."


def build_system_prompt(config_data):
    """Build the system prompt from agent config."""
    base_prompt = config_data.get("system_prompt", "You are a helpful voice assistant.")
    business = config_data.get("business_name", "our business")
    duration = config_data.get("appointment_duration_minutes", 30)
    hours = config_data.get("business_hours", {})

    hours_text = ""
    if hours:
        lines = []
        for day, times in hours.items():
            if times:
                lines.append(f"  {day.capitalize()}: {times['start']} - {times['end']}")
        if lines:
            hours_text = "\n".join(lines)

    return f"""{base_prompt}

Business: {business}
Appointment duration: {duration} minutes
Business hours:
{hours_text or '  Not configured'}

Instructions:
- Always ask for the caller's name and phone number.
- When they want to schedule, use check_availability first to find open slots, then offer them.
- After confirming a slot, use schedule_appointment to book it.
- If the caller wants to be called back, use request_callback.
- Always confirm details before taking any action.
- Be concise — this is a phone call, not a text chat.
- If you cannot help, offer to set up a callback with a team member.
"""


# ── Voice Provider Factory ───────────────────────────────────────────────────

def _get_voice_providers():
    """
    Build STT, LLM, and TTS instances based on VOICE_PROVIDER_MODE env var.

    Supported modes:
      "groq"       — FREE: Groq LLM + Groq Whisper STT + OpenAI-compatible TTS
      "selfhosted" — FREE: vLLM + Faster-Whisper + Kokoro (all on your GPU)
      "openai"     — PAID: GPT-4o-mini + Deepgram STT + OpenAI TTS
    """
    mode = os.environ.get("VOICE_PROVIDER_MODE", "groq")
    logger.info("Voice provider mode: %s", mode)

    if mode == "groq":
        # ── Groq: Free Tier ──────────────────────────────────────────────
        # LLM: Groq's Llama 3.1 (OpenAI-compatible API, free)
        groq_key = os.environ.get("GROQ_API_KEY", "")
        # Default to the 8b "instant" model for live calls — it cuts
        # time-to-first-token from ~1200ms (70b) to ~300ms on Groq, which
        # is the difference between "feels alive" and "feels laggy" on a
        # phone call. Override with GROQ_MODEL=llama-3.1-70b-versatile if
        # you really need the bigger model for a specific deployment.
        groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

        stt = openai.STT(
            model="whisper-large-v3",
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            language="en",
        )
        llm_instance = openai.LLM(
            model=groq_model,
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            temperature=0.7,
        )
        # TTS: OpenAI-compatible endpoint
        # For free testing, Groq doesn't have TTS — so we use OpenAI TTS
        # (costs ~$0.015/1K chars = ~$0.01/min — pennies for testing)
        # OR point to a self-hosted Kokoro TTS if available
        tts_url = os.environ.get("TTS_BASE_URL", "")
        if tts_url:
            tts = openai.TTS(
                model="kokoro",
                voice="af_heart",
                base_url=tts_url,
                api_key="not-needed",
            )
        else:
            tts = openai.TTS(model="tts-1", voice="alloy")

    elif mode == "selfhosted":
        # ── Self-Hosted: All on your GPU ─────────────────────────────────
        vllm_url = os.environ.get("SELFHOSTED_LLM_URL", "http://vllm:8000/v1")
        whisper_url = os.environ.get("SELFHOSTED_STT_URL", "http://whisper:8080/v1")
        kokoro_url = os.environ.get("SELFHOSTED_TTS_URL", "http://kokoro:8880/v1")
        vllm_model = os.environ.get("SELFHOSTED_LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ")

        stt = openai.STT(
            model="Systran/faster-whisper-large-v3",
            base_url=whisper_url,
            api_key="not-needed",
            language="en",
        )
        llm_instance = openai.LLM(
            model=vllm_model,
            base_url=vllm_url,
            api_key="not-needed",
            temperature=0.7,
        )
        tts = openai.TTS(
            model="kokoro",
            voice="af_heart",
            base_url=kokoro_url,
            api_key="not-needed",
        )

    else:
        # ── OpenAI: Paid APIs (default fallback) ─────────────────────────
        if deepgram is not None:
            stt = deepgram.STT(model="nova-2", language="en")
        else:
            stt = openai.STT(model="whisper-1")
        llm_instance = openai.LLM(model="gpt-4o-mini", temperature=0.7)
        tts = openai.TTS(model="tts-1", voice="alloy")

    return stt, llm_instance, tts


def _build_voice_session(system_prompt, stt, llm_instance, tts):
    """Construct a VoiceSession with the system prompt actually wired in.

    Until this fix the worker built the merged KB-aware prompt and then
    silently dropped it on the floor — VoiceSession was instantiated
    without ``chat_ctx``, so the agent ran on the LLM's default behavior.
    Symptom: the agent would ignore business-specific knowledge during
    calls and the prompt_builder cap of 8k chars looked like it had no
    effect because nothing was being sent in the first place.

    livekit-agents 0.x expects ``chat_ctx``; 1.x expects ``instructions``.
    Try both so this file survives an SDK bump without a deploy break.
    """
    kwargs = dict(vad=silero.VAD.load(), stt=stt, llm=llm_instance, tts=tts)

    if ChatContext is not None and system_prompt:
        try:
            ctx = ChatContext()
            # Older SDKs use append(role=, text=); newer ones use add_message.
            if hasattr(ctx, "append"):
                ctx.append(role="system", text=system_prompt)
            elif hasattr(ctx, "add_message"):
                ctx.add_message(role="system", content=system_prompt)
            kwargs["chat_ctx"] = ctx
        except Exception as e:  # noqa: BLE001
            logger.warning("voice_session_chat_ctx_failed: %s", e)

    try:
        return VoiceSession(**kwargs)
    except TypeError:
        # 1.x SDKs that took ``instructions`` instead of ``chat_ctx``.
        kwargs.pop("chat_ctx", None)
        if system_prompt:
            kwargs["instructions"] = system_prompt
        return VoiceSession(**kwargs)


def _create_voice_session(system_prompt, website_id):
    """
    Shared factory: creates a VoiceSession with STT/LLM/TTS, the system
    prompt actually wired in, and tool handlers. Returns an async callable
    ``start(ctx, greeting)`` used by both ``create_voice_agent`` and
    ``run_agent_worker``.
    """
    async def start(ctx, greeting):
        stt, llm_instance, tts = _get_voice_providers()
        agent = _build_voice_session(system_prompt, stt, llm_instance, tts)

        @agent.on("function_call")
        async def on_function_call(call):
            result = await _handle_tool_call(call.name, call.arguments, website_id)
            await call.resolve(result)

        agent.start(ctx.room)
        await agent.say(greeting)

    return start


def create_voice_agent(system_prompt, greeting):
    """
    Create and return a LiveKit agent entrypoint function.

    This function is the entry point for the LiveKit agent worker.
    It returns the agent setup that LiveKit will use for each call.
    """
    if not LIVEKIT_AVAILABLE:
        raise RuntimeError(
            "LiveKit Agents SDK not installed. "
            "Install with: pip install livekit-agents "
            "livekit-plugins-openai livekit-plugins-silero"
        )

    async def entrypoint(ctx: JobContext):
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        website_id = _get_website_id_from_metadata(ctx.room.metadata)
        start = _create_voice_session(system_prompt, website_id)
        await start(ctx, greeting)

    return entrypoint


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def run_agent_worker():
    """
    Start the LiveKit agent worker process.

    Run with:
      VOICE_PROVIDER_MODE=groq \\
      GROQ_API_KEY=gsk_... \\
      LIVEKIT_URL=wss://your-livekit-server.com \\
      LIVEKIT_API_KEY=your-key \\
      LIVEKIT_API_SECRET=your-secret \\
      python -m apps.voice_agent.services.livekit_agent
    """
    if not LIVEKIT_AVAILABLE:
        print(
            "ERROR: LiveKit Agents SDK not installed.\n"
            "Install with:\n"
            "  pip install livekit-agents "
            "livekit-plugins-openai livekit-plugins-silero"
        )
        return

    async def entrypoint(ctx: JobContext):
        import time

        import httpx

        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        meta = _parse_room_metadata(ctx.room.metadata)
        website_id = meta.get("website_id", "")
        call_log_id = meta.get("call_log_id", "")
        welcome_override = meta.get("welcome") or ""

        base = _get_django_api_base()
        token = os.environ.get("LIVEKIT_AGENT_API_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"}

        system_prompt = "You are a helpful voice assistant."
        greeting = "Hello!"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base}/voice-agent/internal/agent-bootstrap/",
                    params={"website_id": website_id},
                    headers=headers,
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    system_prompt = payload.get("system_prompt") or system_prompt
                    greeting = payload.get("greeting") or greeting
                else:
                    logger.warning(
                        "agent_bootstrap_failed status=%s body=%s",
                        resp.status_code, resp.text[:200],
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("agent_bootstrap_error: %s", e)

        # Outbound campaigns provide a per-campaign welcome line that overrides
        # the website's default greeting.
        opening_line = welcome_override or greeting

        stt, llm_instance, tts = _get_voice_providers()
        agent = _build_voice_session(system_prompt, stt, llm_instance, tts)

        transcript_lines: list[str] = []
        # Per-call usage meters captured live and forwarded to the Django
        # /calls/finish/ endpoint, where UsageService rolls them into the
        # monthly usage card.
        meters = {
            "tts_characters": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
        }

        @agent.on("user_speech_committed")
        def _on_user(msg):  # type: ignore[no-redef]
            try:
                transcript_lines.append(f"User: {getattr(msg, 'text', str(msg))}")
            except Exception:  # noqa: BLE001
                pass

        @agent.on("agent_speech_committed")
        def _on_agent(msg):  # type: ignore[no-redef]
            try:
                text = getattr(msg, "text", str(msg))
                transcript_lines.append(f"Agent: {text}")
                # Best-effort TTS character count. The model may emit
                # markdown / SSML; for billing purposes the spoken-text
                # length is the right approximation.
                meters["tts_characters"] += len(text or "")
            except Exception:  # noqa: BLE001
                pass

        @agent.on("metrics_collected")
        def _on_metrics(ev):  # type: ignore[no-redef]
            """LiveKit emits per-segment LLM/TTS metrics. We add them to
            the running totals so the call-finish payload reflects real
            token usage rather than a duration-based estimate."""
            try:
                m = getattr(ev, "metrics", ev)
                # livekit-agents 0.x exposes prompt_tokens / completion_tokens
                pt = getattr(m, "prompt_tokens", None)
                ct = getattr(m, "completion_tokens", None)
                if pt is not None:
                    meters["llm_input_tokens"] += int(pt)
                if ct is not None:
                    meters["llm_output_tokens"] += int(ct)
            except Exception:  # noqa: BLE001
                pass

        @agent.on("function_call")
        async def on_function_call(call):  # type: ignore[no-redef]
            result = await _handle_tool_call(call.name, call.arguments, website_id)
            await call.resolve(result)

        agent.start(ctx.room)
        started_at = time.monotonic()
        await agent.say(opening_line)

        # Wait for the call to end (participant disconnect closes the room).
        try:
            await ctx.wait_for_disconnect()
        except AttributeError:
            # Older SDKs: poll on participant count.
            import asyncio

            while ctx.room.remote_participants:
                await asyncio.sleep(1)

        duration = int(time.monotonic() - started_at)
        if call_log_id:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        f"{base}/voice-agent/internal/calls/finish/",
                        json={
                            "call_log_id": call_log_id,
                            "transcript": "\n".join(transcript_lines),
                            "duration": duration,
                            "ended_reason": "completed",
                            "tts_characters": meters["tts_characters"],
                            "llm_input_tokens": meters["llm_input_tokens"],
                            "llm_output_tokens": meters["llm_output_tokens"],
                            "stt_seconds": duration,
                        },
                        headers=headers,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("call_finish_post_failed: %s", e)

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    run_agent_worker()
