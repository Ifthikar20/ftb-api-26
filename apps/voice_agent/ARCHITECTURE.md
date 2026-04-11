# Voice Agent App

## Purpose

A complete AI-powered phone agent system. Handles both inbound calls (AI receptionist) and outbound calls (AI sales dialer) with real telephony integration, transcript analysis, lead scoring, appointment booking, and CRM-like workflow.

## Architecture

```
Phone Call → Telnyx SIP → LiveKit Server → LiveKit Voice Agent
                                              │
                                   ┌──────────┼──────────┐
                                   ▼          ▼          ▼
                                  STT        LLM        TTS
                            (Speech→Text) (Reasoning) (Text→Speech)
                                   │          │          │
                                   └──────────┼──────────┘
                                              │
                                    Audio back to caller
                                              │
                                    ▼ On call end ▼
                              POST /internal/calls/finish/
                                    │
                           ┌────────┼────────┐
                           ▼        ▼        ▼
                      CallLog   Extraction  Usage
                      update    (Celery)    Service
                                   │
                          ┌────────┼────────┐
                          ▼        ▼        ▼
                      CallTodo  Calendar  Lead Score
                      items     Events    Detection
```

## Provider Modes

Set via `VOICE_PROVIDER_MODE` environment variable:

| Mode | STT | LLM | TTS | Cost |
|---|---|---|---|---|
| `groq` | Groq Whisper Large v3 | Groq Llama 3.1 8B Instant | OpenAI TTS or self-hosted Kokoro | ~$0/min (free tier) |
| `selfhosted` | Faster-Whisper Large v3 | vLLM (Qwen 7B AWQ) | Kokoro TTS | $0/min (own GPU) |
| `openai` | Deepgram Nova-2 | GPT-4o-mini | OpenAI TTS | ~$0.01/min |

## Models (13)

| Model | Purpose |
|---|---|
| `AgentConfig` | Per-website voice agent configuration: system prompt, greeting, business hours, appointment duration, timezone, and business context (markdown). |
| `PhoneNumber` | Work phone numbers with provider (Telnyx/Twilio/Retell), forwarding configuration, and LiveKit outbound trunk IDs. |
| `PhoneVerification` | MFA challenge for phone ownership proof (SMS or voice call with 6-digit OTP). |
| `AgentContextDocument` | Markdown knowledge-base documents injected into the agent system prompt at call time. Sorted by `sort_order`. |
| `CallLog` | Every call with direction, status, caller info, duration, transcript, AI-extracted data, sentiment, intent, lead scoring fields, and per-call billing meters (STT seconds, TTS chars, LLM tokens, estimated cost). |
| `CallExtraction` | Structured data extracted from transcript by LLM: caller info, summary, category, sentiment, follow-ups, detected appointments. |
| `CalendarEvent` | Appointments booked by the agent with Google Calendar / Outlook sync and team member assignment. |
| `CallbackReminder` | Callback reminders with contact info, reason, scheduled time, and status tracking. |
| `CallTodo` | Action items extracted from calls with priority (high/medium/low), status (open/in_progress/done/dismissed), and due dates. |
| `VoiceUsageMonthly` | Pre-aggregated billing per (website, month): call counts, minutes, LLM tokens, TTS chars, estimated cost. |
| `CallCampaign` | Outbound calling campaigns with rate limiting, business hours enforcement, and per-campaign welcome messages. |
| `CallTarget` | Individual recipients in a campaign with retry logic, DNC enforcement, and status tracking. |
| `DoNotCallEntry` | Global do-not-call list for outbound dialing compliance. |

## Services (15)

| Service | Purpose |
|---|---|
| `livekit_agent.py` | LiveKit voice agent worker — the actual AI that runs during calls. Handles tool calls (schedule_appointment, check_availability, request_callback), transcript capture, and usage metering. |
| `livekit_service.py` | LiveKit API client — room creation, agent dispatch, SIP participant management. |
| `call_service.py` | Call lifecycle management — create, update, finish calls. |
| `extraction_service.py` | Post-call LLM analysis — extracts structured data from transcript (caller info, todos, appointments, sentiment). |
| `lead_scoring_service.py` | Scores calls for lead potential from transcript signals (intent, contact info shared, buying keywords). |
| `calendar_service.py` | Appointment booking with availability checking and conflict detection. |
| `prompt_builder.py` | Merges AgentConfig + AgentContextDocuments into a single system prompt (8K char cap). |
| `usage_service.py` | Per-call cost calculation and monthly aggregation into VoiceUsageMonthly. |
| `phone_verification_service.py` | MFA flow: generate OTP, send via SMS/call, verify code. |
| `telnyx_service.py` | Telnyx telephony API: send SMS, place verification calls. |
| `retell_service.py` | Retell AI integration (legacy/alternative provider). |
| `selfhosted_inference.py` | Self-hosted LLM inference client for vLLM/Whisper/Kokoro. |
| `onboarding.py` | Guided setup with industry-specific templates. |
| `tool_handlers.py` | Business logic for agent tool calls (appointment booking, callback creation). |

## Celery Tasks

| Task | Queue | Purpose |
|---|---|---|
| `dispatch_campaign` | ai | Fan out a campaign into individual calls, respecting rate limits and business hours. Self-reschedules every 60s while targets remain. |
| `place_outbound_call` | ai | Place a single outbound call: DNC check → create CallLog → LiveKit room → dispatch agent → SIP dial. Retries up to 3x. |
| `extract_call_data` | ai | Post-call transcript extraction via LLM |
| `sync_calendar_event` | default | Sync appointment to Google Calendar |
| `send_callback_notification` | default | Send in-app + email notification for callback reminders |
| `check_due_reminders` | default | Periodic scan for due callback reminders |

## Frontend (VoiceAgentPage.vue — 1656 lines)

8 tabs:

| Tab | Features |
|---|---|
| Get Started | Onboarding wizard, recent calls preview, industry templates |
| Call Log | Filterable by status/direction, click-through to call details with transcript |
| Todos | AI-extracted action items with priority, status management, caller context |
| Calendar | Appointment list, availability checker, manual booking modal |
| Reminders | Callback reminder cards with complete/dismiss actions |
| Phone Numbers | Add/edit numbers with MFA verification, forwarding toggle |
| Lead Detection | Scored callers with promote-to-lead and dismiss actions |
| Settings | Agent config, business hours, knowledge base document management |

## Test Coverage (13 files, ~2700 lines)

| Test File | Scope |
|---|---|
| `factories.py` | Factory-boy factories for all 13 voice agent models with traits (outbound, missed, with_transcript, with_lead_signals). |
| `test_calendar_service.py` | Availability slots (business hours, exclusions, custom duration), booking with conflict detection, cancellation, status updates, upcoming event filtering. |
| `test_call_service.py` | Call listing/filtering, webhook processing (call_started, call_ended, call_analyzed), call stats aggregation, callback reminder lifecycle. |
| `test_context_document_api.py` | Knowledge base API CRUD, markdown file upload, file type/size validation, Retell sync triggering. |
| `test_extraction_service.py` | Mocked LLM extraction, CallExtraction + CallTodo record creation, caller info backfill, OpenAI fallback, todo management. |
| `test_lead_scoring_service.py` | Individual scoring signals (email, company, intent, sentiment, keywords, appointments, follow-ups), threshold promotion, cap, dismissal, idempotency. |
| `test_onboarding.py` | Template listing, preview, apply, setup status checklist. |
| `test_outbound_dialer.py` | Outbound call placement (DNC check, trunk validation, LiveKit dispatch), campaign fan-out, pause/complete transitions. |
| `test_phone_verification_service.py` | OTP generation, SMS/call dispatch, code verification, expiry, rate limiting. |
| `test_prompt_builder.py` | System prompt assembly from config + context documents, 8K character cap. |
| `test_tool_handlers.py` | schedule_appointment, request_callback, check_availability tool call handlers. |
| `test_usage_service.py` | Cost estimation (floor, rounding, meter combination), monthly rollup, idempotency, dashboard payload. |
| `test_views.py` | API integration tests for config, calls, calendar, todos, reminders, phone numbers, lead detection, usage, and onboarding endpoints. |

## Key Design Decisions

- **Multi-provider flexibility** — Single env var (`VOICE_PROVIDER_MODE`) switches between free (Groq), self-hosted (GPU), and paid (OpenAI) stacks.
- **LiveKit as the real-time backbone** — All voice processing flows through LiveKit rooms, enabling SIP bridging, agent dispatch, and participant management.
- **Post-call intelligence** — Every completed call triggers async extraction (transcript → structured data), lead scoring, and todo creation.
- **Per-call billing meters** — STT seconds, TTS characters, and LLM tokens are tracked per call and rolled into monthly aggregates.
- **DNC compliance** — Outbound dialer checks the DoNotCallEntry table before every call.
- **Business hours enforcement** — Campaigns respect per-website business hours, with auto-reschedule outside hours.

## Dependencies

- **Depends on:** `websites`, `accounts`, `leads`, `notifications`, `core`
- **External:** LiveKit, Telnyx, Groq, OpenAI, Deepgram, Google Calendar API
