# Leads App

## Purpose

Lead capture, scoring, and segmentation. Converts anonymous visitors
(from the analytics pixel) into scored leads with CRM-like workflow.

The email-campaign feature was retired when the product narrowed
focus to LLM Ranking + GEO. `EmailCampaign`, `CampaignRecipient`,
`MailchimpService`, the Resend / SES senders, and the open-pixel
endpoint were all removed.

## Architecture

```
Visitor (analytics app)
  │
  └── Behavioral scoring (page views, scroll depth, form fills)
        │
        ▼
      Lead created (score >= threshold)
        │
        ├── Assigned to team member
        ├── Status pipeline: new → contacted → qualified → proposal → won/lost
        └── Notes, emails, segments

ScoringConfig (per-website weights + ML model version)
  └── Daily rescore via Celery
```

## Models

| Model | Purpose |
|---|---|
| `Lead` | A scored lead derived from a Visitor. 1:1 with `analytics.Visitor`. Tracks score, status pipeline, assignment, source, and contact info. Supports soft delete. |
| `LeadNote` | Team notes on a lead, authored by a user. |
| `LeadSegment` | Saved filter segments (JSON rules) for grouping leads (e.g., "High-intent from organic search"). |
| `ScoringConfig` | Per-website scoring configuration: weight overrides (JSON), threshold for lead creation, and ML model version. |
| `LeadEmail` | Individual emails sent to leads from the platform. |

## Services

| Service | Purpose |
|---|---|
| `LeadScoringService` | Applies scoring weights to visitor behavior data |
| `DeduplicationService` | Merges duplicate leads, re-parenting notes + emails |
| `TimelineService` | Aggregates page events, notes, and emails into a per-lead timeline |
| `DriveService` | Google Drive integration for lead exports |
| `OpenClawService` | OpenClaw lead-search integration |

## Celery Tasks

| Task | Schedule | Purpose |
|---|---|---|
| `rescore_all_leads` | Daily at 2 AM | Re-score all leads across all websites with latest behavioral data |

## Key Design Decisions

- **Visitor-first model** — Leads are derived from Visitors (1:1 FK), so all behavioral data is preserved.
- **Soft delete** — Leads use `SoftDeleteMixin` for GDPR compliance (recoverable deletion).
- **Configurable scoring** — `ScoringConfig` allows per-website weight tuning and supports ML model versioning for future advanced scoring.

## Dependencies

- **Depends on:** `analytics` (Visitor model), `websites`, `accounts`, `core`
- **Depended on by:** `social_leads` (social lead → FetchBot lead)
