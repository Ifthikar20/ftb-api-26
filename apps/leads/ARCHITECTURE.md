# Leads App

## Purpose

Lead capture, scoring, segmentation, and email campaign management. Converts anonymous visitors (from the analytics pixel) into scored leads with CRM-like workflow, and enables outbound email campaigns with full-funnel attribution.

## Architecture

```
Visitor (analytics app)
  │
  ├── Behavioral scoring (page views, scroll depth, form fills)
  │     │
  │     ▼
  │   Lead created (score >= threshold)
  │     │
  │     ├── Assigned to team member
  │     ├── Status pipeline: new → contacted → qualified → proposal → won/lost
  │     └── Notes, emails, segments
  │
  ├── Email Campaigns
  │     ├── EmailCampaign (subject, body, segment filter)
  │     ├── CampaignRecipient (per-lead tracking)
  │     │     ├── tracking_id → email open pixel
  │     │     └── TrackedLink clicks → LinkClick attribution
  │     └── Stats: recipient_count, open_count, click_count
  │
  └── Lead Scoring
        └── ScoringConfig (per-website weights + ML model version)
              └── Daily rescore via Celery
```

## Models

| Model | Purpose |
|---|---|
| `Lead` | A scored lead derived from a Visitor. 1:1 with `analytics.Visitor`. Tracks score, status pipeline, assignment, source, and contact info. Supports soft delete. |
| `LeadNote` | Team notes on a lead, authored by a user. |
| `LeadSegment` | Saved filter segments (JSON rules) for grouping leads (e.g., "High-intent from organic search"). |
| `ScoringConfig` | Per-website scoring configuration: weight overrides (JSON), threshold for lead creation, and ML model version. |
| `EmailCampaign` | Outbound email campaigns with HTML body, segment targeting, Mailchimp sync, and open/click tracking. |
| `CampaignRecipient` | Individual recipient tracking within a campaign: queued → sent → opened → clicked → bounced. Each gets a unique `tracking_id` for pixel/link attribution. |
| `LeadEmail` | Individual emails sent to leads from the platform (outside of campaigns). |

## Services

| Service | Purpose |
|---|---|
| `LeadScoringService` | Applies scoring weights to visitor behavior data |
| `MailchimpService` | Syncs campaigns and segments with Mailchimp |
| `DriveService` | Google Drive integration for lead exports |

## Celery Tasks

| Task | Schedule | Purpose |
|---|---|---|
| `rescore_all_leads` | Daily at 2 AM | Re-score all leads across all websites with latest behavioral data |

## Key Design Decisions

- **Visitor-first model** — Leads are derived from Visitors (1:1 FK), so all behavioral data is preserved.
- **Soft delete** — Leads use `SoftDeleteMixin` for GDPR compliance (recoverable deletion).
- **Configurable scoring** — `ScoringConfig` allows per-website weight tuning and supports ML model versioning for future advanced scoring.
- **Full-funnel attribution** — CampaignRecipient → TrackedLink → LinkClick chain enables tracking from email send through to website conversion.
- **Mailchimp sync** — Campaigns can be synced with Mailchimp for delivery, keeping FetchBot as the analytics layer.

## Dependencies

- **Depends on:** `analytics` (Visitor model), `websites`, `accounts`, `core`
- **Depended on by:** `social_leads` (social lead → FetchBot lead)
