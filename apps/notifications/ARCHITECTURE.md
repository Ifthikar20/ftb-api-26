# Notifications App

## Purpose

Multi-channel notification system — in-app, email, Slack, Discord, and Telegram. Handles real-time alerts (hot leads, keyword changes), scheduled digests (daily/weekly reports), and user-configurable notification preferences.

## Architecture

```
Event Source (any app)
  │
  ├── In-app: Notification.objects.create(...)
  │     └── WebSocket push via Django Channels (routing.py)
  │
  ├── Email: SendGrid / Django send_mail
  │
  └── External Integrations:
        IntegrationConnection (Slack/Discord/Telegram)
          ├── Webhook URL (encrypted)
          ├── Schedule (realtime / daily / weekly)
          ├── Format (summary / detailed)
          └── Event filters (daily_report, hot_leads, trend_digest, milestones)
```

## Models

| Model | Purpose |
|---|---|
| `Notification` | In-app notification with type, title, message, data (JSON), read status, and action URL for deep linking. |
| `NotificationPreference` | Per-user channel preferences: hot lead email/Slack, weekly report, competitor changes, audit complete. Includes encrypted Slack webhook URL. |
| `IntegrationConnection` | External platform connection (Slack, Discord, Telegram). Stores encrypted webhook URL, channel name, schedule config, message format, and per-type notification toggles. |

## Notification Types

| Type | Channels | Trigger |
|---|---|---|
| Hot lead detected | In-app, email, Slack | Lead score crosses threshold |
| Keyword rank change | In-app, email | Keyword alert fires |
| Competitor change | In-app | Weekly crawl detects change |
| Audit completed | In-app | LLM ranking audit finishes |
| Weekly report | Email, Slack/Discord/Telegram | Monday 9 AM Celery beat |
| Voice agent callback | In-app, email | Callback reminder due |

## WebSocket Support

- `routing.py` — Defines WebSocket URL patterns for real-time notification delivery.
- Notifications can be pushed to connected clients instantly via Django Channels.

## Celery Tasks

| Task | Schedule | Purpose |
|---|---|---|
| `send_weekly_reports` | Monday 9 AM | Generate and send weekly analytics digests |

## Key Design Decisions

- **Encrypted webhook URLs** — `EncryptedTextField` for Slack/Discord/Telegram webhooks, protecting credentials at rest.
- **User-controlled frequency** — Users choose per-integration whether to receive messages in real-time, daily, or weekly.
- **Message format options** — Summary (condensed) or detailed (full data) to match different team workflows.
- **Unique per platform** — `unique_together = [("user", "platform")]` ensures one connection per platform per user.

## Dependencies

- **Depends on:** `accounts`, `core` (encryption)
- **Depended on by:** `voice_agent` (callback notifications), `analytics` (keyword alerts), `billing` (trial ending), `agents` (agent completion)
