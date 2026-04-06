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
        Agent,
        AgentSession,
        AutoSubscribe,
        JobContext,
        WorkerOptions,
        cli,
        llm,
    )
    from livekit.agents.voice import VoiceSession
    from livekit.plugins import openai, silero

    # Optional plugins — only needed for specific provider modes
    try:
        from livekit.plugins import deepgram
    except ImportError:
        deepgram = None

    LIVEKIT_AVAILABLE = True
except ImportError:
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


def _get_website_id_from_metadata(metadata):
    """Extract website_id from room metadata."""
    import json

    try:
        data = json.loads(metadata) if isinstance(metadata, str) else metadata
        return data.get("website_id", "")
    except (json.JSONDecodeError, TypeError):
        return ""


async def _handle_tool_call(tool_name, arguments, website_id):
    """
    Execute a tool call by hitting the Django API.
    This runs during the call to schedule appointments, check availability, etc.
    """
    import json

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
        groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")

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


def _create_voice_session(system_prompt, website_id):
    """
    Shared factory: creates a VoiceSession with STT/LLM/TTS and tool handlers.
    Returns an async callable(ctx, greeting) that starts the session.

    Used by both create_voice_agent() and run_agent_worker() to avoid duplication.
    """
    async def start(ctx, greeting):
        stt, llm_instance, tts = _get_voice_providers()

        agent = VoiceSession(
            vad=silero.VAD.load(),
            stt=stt,
            llm=llm_instance,
            tts=tts,
        )

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
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        website_id = _get_website_id_from_metadata(ctx.room.metadata)

        # Fetch config from Django API
        import httpx

        config_data = {}
        try:
            base = _get_django_api_base()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base}/voice-agent/{website_id}/config/",
                    headers={
                        "Authorization": f"Bearer {os.environ.get('LIVEKIT_AGENT_API_TOKEN', '')}",
                    },
                )
                if resp.status_code == 200:
                    config_data = resp.json().get("data", resp.json())
        except Exception as e:
            logger.warning("Failed to fetch agent config: %s", e)

        system_prompt = build_system_prompt(config_data)
        greeting = config_data.get(
            "greeting_message",
            "Hello! Thank you for calling. How can I help you today?",
        )

        # Reuse the shared agent factory
        _start_session = _create_voice_session(system_prompt, website_id)
        await _start_session(ctx, greeting)

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    run_agent_worker()
