# Voice Agent — Complete Technical Reference

## Overview

The FetchBot Voice Agent is an AI-powered phone answering system that handles inbound and outbound calls, books appointments, captures lead information, and creates action items — all without human intervention. It supports three deployment backends: Retell AI (fully managed), LiveKit (self-hosted telephony stack), and a fully self-hosted option.

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [Phone Number Setup](#2-phone-number-setup)
3. [How a Call Is Handled — Step by Step](#3-how-a-call-is-handled--step-by-step)
4. [Agent Context Documents](#4-agent-context-documents)
5. [AI System Prompt Construction](#5-ai-system-prompt-construction)
6. [Post-Call Processing](#6-post-call-processing)
7. [Social Media Lead Integration](#7-social-media-lead-integration)
8. [Deployment Backends](#8-deployment-backends)
9. [Webhook Reference](#9-webhook-reference)
10. [Configuration Reference](#10-configuration-reference)
11. [Cost Comparison](#11-cost-comparison)

---

## 1. Architecture

```
Caller dials phone number
        |
        v
  [Telephony Provider]
  (Telnyx / Twilio / Retell)
        |
        | SIP/PSTN
        v
  [Voice Backend]
  Retell AI   OR   LiveKit + Deepgram + Kokoro TTS
        |
        | call events (webhook)
        v
  [FetchBot API]  /api/v1/voice-agent/webhook/retell/
        |
        |-- AgentConfig (loads system prompt + context docs)
        |-- CallLog (creates record)
        |-- ExtractionService (post-call AI analysis)
        |-- CalendarEvent / CallbackReminder / CallTodo
        |
        v
  [Business Dashboard]  /voice-agent/:websiteId
```

Key components:

| Component | Purpose |
|---|---|
| `AgentConfig` | Per-website config: system prompt, greeting, business hours |
| `PhoneNumber` | Work phone numbers added by the user |
| `AgentContextDocument` | Markdown knowledge base files injected into the agent prompt |
| `CallLog` | Record of every call with transcript and extracted data |
| `CalendarEvent` | Appointments booked during calls |
| `CallbackReminder` | Callback requests made by callers |
| `CallTodo` | AI-extracted action items from call transcripts |
| `CallExtraction` | Full structured JSON extracted by the LLM post-call |
| `ExtractionService` | Runs after every call, parses transcript into structured data |
| `RetellService` | Manages Retell AI agents, phone numbers, webhooks |

---

## 2. Phone Number Setup

### Adding a Work Phone Number

1. Go to **Voice Agent** > **Phone Numbers** tab.
2. Click **Add Phone Number**.
3. Enter the number in E.164 format (e.g. `+12025551234`).
4. Give it a label (e.g. "Main Line", "Sales Line").
5. Select the provider: Telnyx, Twilio, or Retell.
6. Optionally enable **Forward to Agent** — this routes calls from this number into the AI agent.
7. Click **Save**.

### How Forwarding Works

When a caller dials your work phone number:

```
Caller --> Your Work Number (e.g. +1 800 555 0100)
                |
                | (call forwarding via SIP or PSTN forward)
                v
         Retell AI / LiveKit endpoint
                |
                | (AI handles the call)
                v
         Webhook fires to FetchBot
                |
                v
         CallLog created, transcript stored
```

The `forwarding_number` field in `AgentConfig` stores the SIP/telephony endpoint that your phone provider forwards to. You configure call forwarding once in your carrier's portal.

### Phone Number Providers

| Provider | Cost/min | Notes |
|---|---|---|
| Telnyx | ~$0.005 | Lowest cost, SIP trunking |
| Twilio | ~$0.0085 | Easy setup, higher cost |
| Retell AI | Included | Agent + number bundled |

---

## 3. How a Call Is Handled — Step by Step

### Step 1 — Caller dials

The caller dials a phone number connected to the voice agent. This can be:
- A Retell AI managed number (purchased via API)
- A Telnyx/Twilio number forwarded to LiveKit SIP endpoint
- A number forwarded from your existing business line

### Step 2 — Voice backend answers

**Retell AI path:**
- Retell receives the call and connects it to the configured agent
- The agent's system prompt is pre-loaded from the last `activate` call
- Retell streams STT (speech-to-text), sends text to LLM, streams TTS back

**LiveKit path:**
- Telnyx SIP trunk routes call to LiveKit SIP server
- Deepgram handles real-time speech-to-text
- GPT-4o-mini / Qwen generates responses
- Kokoro TTS or ElevenLabs generates voice audio

### Step 3 — Agent greets the caller

The agent speaks the configured `greeting_message`:

```
"Hello! Thank you for calling [Business Name]. I'm an AI assistant.
How can I help you today?"
```

### Step 4 — AI handles the conversation

The LLM uses the full system prompt (see Section 5) to:
- Answer questions about the business (from context documents)
- Schedule appointments (calling the `schedule_appointment` tool)
- Record callback requests (calling the `request_callback` tool)
- Check available time slots (calling the `check_availability` tool)
- Capture caller name, email, and company

### Step 5 — Tool calls during the call

When the agent needs to take action, it calls internal tools:

**schedule_appointment**
```json
{
  "attendee_name": "John Smith",
  "attendee_phone": "+12025551234",
  "attendee_email": "john@example.com",
  "date": "2026-04-10",
  "time": "14:00",
  "title": "Discovery Call",
  "duration_minutes": 30
}
```
FetchBot creates a `CalendarEvent` and responds with confirmation.

**request_callback**
```json
{
  "contact_name": "Jane Doe",
  "contact_phone": "+12025550000",
  "reason": "Needs pricing information",
  "preferred_time": "tomorrow morning"
}
```
FetchBot creates a `CallbackReminder` and schedules a notification.

**check_availability**
```json
{
  "date": "2026-04-10"
}
```
FetchBot returns available time slots based on `business_hours` and existing `CalendarEvent` records.

### Step 6 — Call ends

When the call ends, the voice backend fires a `call_ended` webhook to `/api/v1/voice-agent/webhook/retell/`.

The webhook handler:
1. Updates `CallLog.status` to `completed`
2. Stores `transcript`, `summary`, `duration_seconds`
3. Queues the `extract_call_data` Celery task

### Step 7 — Post-call extraction (async)

`ExtractionService` runs within seconds of the call ending:

1. Sends the transcript to the self-hosted LLM (or GPT-4o-mini fallback)
2. Extracts structured data using guided JSON decoding:
   - Caller name, phone, email, company
   - Call category (appointment, inquiry, complaint, sales, support, other)
   - Sentiment (positive, neutral, negative, frustrated)
   - Action items with priority and due date
   - Appointments detected in conversation
   - Follow-up urgency
3. Creates `CallExtraction` record
4. Creates `CallTodo` records for each action item
5. Links call to existing `Lead` if email matches

### Step 8 — Dashboard updates

The business owner sees:
- New call in the **Call Log** tab with transcript and sentiment
- New todos in **Todos** tab (AI-extracted action items)
- New appointment in **Calendar** tab (if booked)
- New reminder in **Reminders** tab (if callback requested)

---

## 4. Agent Context Documents

Context documents are Markdown files that give the AI agent knowledge about your business. They are injected directly into the system prompt at call time.

### What to put in context documents

Create one document per topic area:

**Services & Pricing**
```markdown
# Services

## Web Development
- Custom websites: $3,000 - $15,000
- E-commerce stores: $5,000 - $20,000
- Maintenance packages: $200/month

## SEO Services
- Monthly retainer: $1,500/month
- One-time audit: $500
- Minimum contract: 3 months
```

**Frequently Asked Questions**
```markdown
# FAQs

## Do you offer payment plans?
Yes. We offer 50% upfront and 50% on delivery for all projects over $2,000.

## How long does a website take?
Standard websites: 4-6 weeks. E-commerce: 8-12 weeks.

## Do you work with small businesses?
Absolutely. We have packages starting at $1,000 for landing pages.
```

**Policies & Procedures**
```markdown
# Policies

## Refund Policy
We offer full refunds within 7 days of project start if no work has begun.

## Revision Policy
Each project includes 2 rounds of revisions. Additional revisions are $75/hour.
```

**Team & Contact**
```markdown
# Team

## Sales Team
- Sarah Johnson - Head of Sales - sarah@acme.com
- Available Mon-Fri 9am-5pm EST

## Support Team
- support@acme.com
- Response time: within 4 business hours
```

### Managing Context Documents

1. Go to **Voice Agent** > **Settings** > **Knowledge Base** section.
2. Click **Add Document**.
3. Give it a title (e.g. "Services & Pricing").
4. Paste or type the Markdown content.
5. Toggle **Active** to include it in calls.
6. Click **Save**.

Active documents are concatenated and injected into the system prompt whenever a call starts. Keep each document focused on one topic for best results.

### Context Document Limits

- Maximum document size: 10,000 characters each
- Maximum total context: 50,000 characters
- Documents over the limit are truncated with a warning

---

## 5. AI System Prompt Construction

When a call starts, the agent's full system prompt is assembled as follows:

```
[ROLE DEFINITION]
You are [Business Name]'s AI voice assistant. You are professional, friendly,
and concise — you are on a phone call so keep responses brief.

[CORE INSTRUCTIONS]
- Always confirm caller details before booking appointments
- If you cannot answer a question, offer to have a human call back
- Capture the caller's name and phone number early in the conversation
- Never make up information — only use the knowledge base below

[BUSINESS CONTEXT]
Business Name: [business_name]
Timezone: [timezone]
Appointment Duration: [appointment_duration_minutes] minutes

Business Hours:
- Monday: 9:00 AM - 5:00 PM
- Tuesday: 9:00 AM - 5:00 PM
...

[KNOWLEDGE BASE]
--- Services & Pricing ---
[content of Services document]

--- FAQs ---
[content of FAQ document]

--- Policies ---
[content of Policies document]

[TOOLS AVAILABLE]
- schedule_appointment: Book a meeting in the calendar
- check_availability: Check open time slots for a date
- request_callback: Record a callback request for the team
```

The `system_prompt` field in `AgentConfig` is the customizable core of this. Context documents are appended after it automatically.

---

## 6. Post-Call Processing

### Extraction Pipeline

```
call_ended webhook
        |
        v
extract_call_data.delay(call_log_id)  [Celery task]
        |
        v
ExtractionService.extract_from_transcript(call_log)
        |
        |-- POST transcript to self-hosted LLM (/v1/chat/completions)
        |   with JSON schema guidance
        |
        |-- Parse response into CallExtraction record
        |
        |-- For each action_item: create CallTodo
        |
        |-- If caller email matches Lead: link CallLog.lead
        |
        v
CallExtraction saved
CallTodo records saved
CallLog.lead linked (if matched)
```

### Extraction Schema

The LLM is guided to output this exact JSON structure:

```json
{
  "caller_info": {
    "name": "John Smith",
    "phone": "+12025551234",
    "email": "john@example.com",
    "company": "Acme Corp"
  },
  "call_summary": "Caller inquired about web development pricing. Interested in e-commerce store. Budget around $8,000. Booked discovery call for April 10th.",
  "call_category": "appointment",
  "sentiment": "positive",
  "action_items": [
    {
      "description": "Send John e-commerce portfolio examples",
      "priority": "high",
      "due_date": "2026-04-08"
    }
  ],
  "appointments": [
    {
      "date": "2026-04-10",
      "time": "14:00",
      "duration_minutes": 30,
      "description": "Discovery call",
      "confirmed": true
    }
  ],
  "follow_ups": [
    {
      "description": "Follow up if John doesn't respond to portfolio email",
      "urgency": "within_24h"
    }
  ]
}
```

### Sentiment Categories

| Value | Meaning |
|---|---|
| `positive` | Caller was satisfied, engaged, or happy |
| `neutral` | Standard transactional interaction |
| `negative` | Caller expressed dissatisfaction |
| `frustrated` | Caller was clearly upset or annoyed |

### Call Categories

| Value | When used |
|---|---|
| `appointment` | Caller books or inquires about a meeting |
| `inquiry` | General information request |
| `complaint` | Caller has a problem or grievance |
| `support` | Technical or service support |
| `sales` | Pricing, proposals, purchase intent |
| `other` | Does not fit above |

---

## 7. Social Media Lead Integration

Leads captured from Facebook, LinkedIn, and X are automatically imported into the leads pipeline and can trigger outbound voice agent calls.

### Facebook Lead Ads

**Setup:**
1. Go to **Integrations** > **Facebook Lead Ads**.
2. Connect your Facebook Business account (OAuth).
3. Select the ad account and lead form.
4. FetchBot registers a webhook to receive new leads in real time.

**Flow:**
```
User submits Facebook Lead Ad form
        |
        v
Facebook sends webhook to /api/v1/social-leads/webhook/facebook/
        |
        v
FetchBot creates Lead record
        |
        v
(Optional) Triggers outbound call via voice agent
```

**Data captured:**
- Full name, email, phone number
- Form field answers (custom questions)
- Ad campaign and form name
- Lead timestamp

### LinkedIn Lead Gen Forms

**Setup:**
1. Go to **Integrations** > **LinkedIn Lead Gen**.
2. Connect your LinkedIn Campaign Manager account.
3. Select the lead gen form.
4. FetchBot polls LinkedIn API every 15 minutes for new leads (LinkedIn does not support real-time webhooks).

**Flow:**
```
User submits LinkedIn Lead Gen Form
        |
        v
FetchBot polls /v2/leadGenFormResponses every 15 min
        |
        v
New responses imported as Lead records
        |
        v
(Optional) Triggers outbound call or email campaign
```

**Data captured:**
- First name, last name, email
- LinkedIn profile URL
- Job title, company, industry
- Form questions and answers

### X (Twitter) Leads

X does not provide a native lead generation form product. FetchBot supports two collection methods:

**Method 1 — X Cards with landing page pixel**
Use X Promoted Posts with a link to your website. The FetchBot tracking pixel captures visitors from X and scores them as leads based on page behavior.

**Method 2 — Manual import**
Export leads from X Ads Manager (CSV) and import them via the **Leads** > **Import CSV** feature.

### Other Platforms

| Platform | Integration Method |
|---|---|
| Instagram | Via Facebook Lead Ads (same Meta API) |
| TikTok | Webhook via TikTok Lead Generation API |
| Google Ads | Lead form extensions via Google Ads API |
| HubSpot | Bidirectional sync via HubSpot OAuth |
| Mailchimp | Audience sync for email campaigns |

---

## 8. Deployment Backends

### Option A — Retell AI (Managed)

Easiest setup. Everything runs in Retell's cloud.

**Required env vars:**
```
RETELL_API_KEY=key_xxxx
VOICE_AGENT_BACKEND=retell
```

**Setup steps:**
1. Create Retell account at retell.ai
2. Generate API key
3. Set `RETELL_API_KEY` in environment
4. Click "Activate Agent" in FetchBot — this calls `RetellService.create_agent()`
5. Purchase phone number in FetchBot — calls `RetellService.purchase_phone_number()`
6. Callers can now dial the number and reach the AI

**How Retell processes a call:**
1. Caller dials Retell phone number
2. Retell sends audio to Deepgram STT (included)
3. Text goes to the LLM (GPT-4o by default)
4. LLM response goes to ElevenLabs TTS (included)
5. Audio returned to caller
6. When call ends, Retell fires webhook to FetchBot

### Option B — Self-Hosted via LiveKit

Full control. 88% cheaper than Retell.

**Stack:**
- **Telnyx** — SIP trunk ($0.005/min)
- **Deepgram** — Speech-to-text ($0.004/min)
- **GPT-4o-mini / Qwen** — LLM ($0.0002/min)
- **Kokoro TTS** — Text-to-speech (self-hosted, $0/min after GPU cost)
- **LiveKit** — WebRTC/SIP orchestration

**Required env vars:**
```
VOICE_AGENT_BACKEND=livekit
LIVEKIT_URL=wss://your-livekit.example.com
LIVEKIT_API_KEY=API_xxx
LIVEKIT_API_SECRET=secret_xxx
DEEPGRAM_API_KEY=dg_xxx
```

**Infrastructure setup:**
1. Deploy LiveKit server (Docker or cloud)
2. Configure Telnyx SIP trunk to point at LiveKit SIP endpoint
3. Deploy Kokoro TTS server (`docker/voice-agent/kokoro-tts/server.py`)
4. Set environment variables
5. Click "Activate Agent" in FetchBot

### Option C — Fully Self-Hosted (No External APIs)

Complete privacy — no data leaves your infrastructure.

**Stack:**
- **Asterisk / FreeSWITCH** — PBX/telephony
- **Whisper (local)** — STT
- **Qwen 2.5 7B AWQ** — LLM (quantized, fits on 8GB VRAM)
- **Kokoro TTS** — TTS

**Required env vars:**
```
VOICE_AGENT_BACKEND=selfhosted
SELFHOSTED_LLM_URL=http://localhost:8000/v1
SELFHOSTED_STT_URL=http://localhost:8001/v1
SELFHOSTED_TTS_URL=http://localhost:8002
SELFHOSTED_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
```

**Fine-tuning (optional):**
Use `scripts/voice-agent/finetune.py` to fine-tune the LLM on your specific business domain for better accuracy.

---

## 9. Webhook Reference

### POST /api/v1/voice-agent/webhook/retell/

Receives all Retell AI call lifecycle events. Verified via HMAC-SHA256 signature.

**Headers:**
```
X-Retell-Signature: sha256=...
```

**Event: call_started**
```json
{
  "event": "call_started",
  "data": {
    "call_id": "call_abc123",
    "agent_id": "agent_xyz",
    "from_number": "+12025551234",
    "to_number": "+18005550100",
    "direction": "inbound"
  }
}
```
Creates a `CallLog` with status `in_progress`.

**Event: call_ended**
```json
{
  "event": "call_ended",
  "data": {
    "call_id": "call_abc123",
    "duration_ms": 180000,
    "transcript": "Agent: Hello...\nCaller: Hi...",
    "summary": "Caller inquired about pricing."
  }
}
```
Updates `CallLog` to `completed`, queues extraction task.

**Event: call_analyzed**
```json
{
  "event": "call_analyzed",
  "data": {
    "call_id": "call_abc123",
    "call_analysis": {
      "sentiment": "positive",
      "call_successful": true,
      "custom_analysis_data": {}
    }
  }
}
```
Updates `CallLog.sentiment` and extracted analysis data.

**Event: tool_call**
```json
{
  "event": "tool_call",
  "data": {
    "call_id": "call_abc123",
    "tool_call": {
      "id": "tool_001",
      "name": "schedule_appointment",
      "arguments": {
        "attendee_name": "John Smith",
        "date": "2026-04-10",
        "time": "14:00"
      }
    }
  }
}
```
Executes the tool and returns result to Retell to read aloud.

### POST /api/v1/social-leads/webhook/facebook/

Receives new leads from Facebook Lead Ads. Verified via X-Hub-Signature-256 header.

### GET /api/v1/social-leads/webhook/facebook/

Facebook webhook verification (hub.challenge echo).

---

## 10. Configuration Reference

### AgentConfig fields

| Field | Type | Description |
|---|---|---|
| `is_active` | bool | Whether the agent is enabled |
| `retell_agent_id` | string | Retell agent ID (set on activation) |
| `phone_number` | string | Primary E.164 phone number |
| `greeting_message` | text | First words spoken to caller |
| `system_prompt` | text | Core AI instructions |
| `business_context` | text | Legacy inline context (prefer context docs) |
| `business_name` | string | Spoken name of business |
| `forwarding_number` | string | SIP/telephony forward destination |
| `business_hours` | JSON | `{"monday": {"start": "09:00", "end": "17:00"}, ...}` |
| `appointment_duration_minutes` | int | Default slot length (15-120 min) |
| `timezone` | string | IANA timezone (e.g. `America/New_York`) |

### PhoneNumber fields

| Field | Type | Description |
|---|---|---|
| `number` | string | E.164 phone number |
| `label` | string | Human label (e.g. "Sales Line") |
| `provider` | string | `telnyx`, `twilio`, or `retell` |
| `is_active` | bool | Whether forwarding is enabled |
| `forwarded_to_agent` | bool | Route calls to AI agent |

### AgentContextDocument fields

| Field | Type | Description |
|---|---|---|
| `title` | string | Document name shown in UI |
| `content` | text | Markdown content |
| `is_active` | bool | Include in system prompt |
| `sort_order` | int | Order documents appear in prompt |

---

## 11. Cost Comparison

| Solution | Per minute | 10K min/month |
|---|---|---|
| Retell AI (managed) | $0.14 - $0.27 | $1,400 - $2,700 |
| LiveKit self-hosted | ~$0.017 | ~$170 |
| Fully self-hosted | ~$0.006 | ~$60 (GPU only) |

### LiveKit cost breakdown (per minute)

| Component | Cost |
|---|---|
| Telnyx SIP | $0.005 |
| Deepgram STT | $0.004 |
| GPT-4o-mini | $0.0002 |
| Kokoro TTS (self-hosted) | $0.003 |
| GPU infrastructure | $0.006 |
| **Total** | **~$0.017** |

---

## Quick Start Checklist

- [ ] Set `RETELL_API_KEY` (or LiveKit env vars) in `.env`
- [ ] Go to Voice Agent settings and enter business name and greeting
- [ ] Add at least one context document (Services & Pricing is most important)
- [ ] Configure business hours and timezone
- [ ] Click Activate Agent
- [ ] Add a phone number or configure call forwarding
- [ ] Make a test call to verify the agent responds correctly
- [ ] Review the first call log to confirm extraction is working
- [ ] Set up Facebook / LinkedIn integrations to pipe social leads in
