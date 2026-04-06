"""
LiveKit Voice Agent — self-hosted voice pipeline.

Architecture:
  Phone Call -> Telnyx SIP -> LiveKit Server -> This Agent
                                                  |
                                      Deepgram STT (streaming)
                                                  |
                                      GPT-4o-mini (OpenAI API)
                                                  |
                                      Kokoro TTS (self-hosted)
                                                  |
                                          Audio back to caller

Cost: ~$0.017/min vs $0.14-0.27/min on Retell AI (88-94% savings)

Requirements:
  pip install livekit-agents livekit-plugins-deepgram livekit-plugins-openai livekit-plugins-silero

To run:
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
    from livekit.plugins import deepgram, openai, silero

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


def create_voice_agent(system_prompt, greeting):
    """
    Create and return a LiveKit voice agent configuration.

    This function is the entry point for the LiveKit agent worker.
    It returns the agent setup that LiveKit will use for each call.
    """
    if not LIVEKIT_AVAILABLE:
        raise RuntimeError(
            "LiveKit Agents SDK not installed. "
            "Install with: pip install livekit-agents livekit-plugins-deepgram "
            "livekit-plugins-openai livekit-plugins-silero"
        )

    async def entrypoint(ctx: JobContext):
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        website_id = _get_website_id_from_metadata(ctx.room.metadata)

        # Build the LLM with tools
        model = openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7,
        )

        agent = VoiceSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(
                model="nova-2",
                language="en",
            ),
            llm=model,
            tts=openai.TTS(
                model="tts-1",
                voice="alloy",
            ),
            # For self-hosted Kokoro TTS, replace above with:
            # tts=KokoroTTS(model_path="/path/to/kokoro", voice="default"),
        )

        # Register tool handlers
        @agent.on("function_call")
        async def on_function_call(call):
            result = await _handle_tool_call(call.name, call.arguments, website_id)
            await call.resolve(result)

        agent.start(ctx.room)

        # Send greeting
        await agent.say(greeting)

    return entrypoint


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def run_agent_worker():
    """
    Start the LiveKit agent worker process.

    Run with:
      LIVEKIT_URL=wss://your-livekit-server.com \\
      LIVEKIT_API_KEY=your-key \\
      LIVEKIT_API_SECRET=your-secret \\
      DEEPGRAM_API_KEY=your-key \\
      OPENAI_API_KEY=your-key \\
      python -m apps.voice_agent.services.livekit_agent
    """
    if not LIVEKIT_AVAILABLE:
        print(
            "ERROR: LiveKit Agents SDK not installed.\n"
            "Install with:\n"
            "  pip install livekit-agents livekit-plugins-deepgram "
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

        model = openai.LLM(model="gpt-4o-mini", temperature=0.7)

        agent = VoiceSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-2", language="en"),
            llm=model,
            tts=openai.TTS(model="tts-1", voice="alloy"),
        )

        @agent.on("function_call")
        async def on_function_call(call):
            result = await _handle_tool_call(call.name, call.arguments, website_id)
            await call.resolve(result)

        agent.start(ctx.room)
        await agent.say(greeting)

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    run_agent_worker()
