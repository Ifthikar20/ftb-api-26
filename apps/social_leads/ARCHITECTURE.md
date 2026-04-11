# Social Leads App

## Purpose

Captures leads from social media platform lead forms (Facebook Lead Ads, Instagram, LinkedIn Lead Gen Forms, TikTok, X, Google Lead Form Extensions) and imports them into the FetchBot lead pipeline. Bridges paid social advertising with the CRM.

## Architecture

```
Social Media Platform
  │
  ├── Webhook push (Facebook, LinkedIn)
  │     POST /api/v1/social-leads/webhook/<source_id>/
  │       ├── Verify webhook (hub.verify_token for Facebook)
  │       └── Create SocialLead from form data
  │
  ├── Polling (TikTok, Google)
  │     Celery task fetches new leads via API
  │
  └── SocialLead created
        │
        ├── Auto-create FetchBot Lead (leads app)
        │     ├── Create analytics.Visitor (fingerprinted from contact info)
        │     └── Create leads.Lead (linked 1:1 to SocialLead)
        │
        └── Optional: Queue outbound voice call (voice_agent app)
              └── voice_call_queued = True
```

## Models

| Model | Purpose |
|---|---|
| `SocialLeadSource` | Configuration for a platform connection. Stores platform type, account/form/campaign IDs, OAuth tokens (access + refresh), webhook verification token, and sync stats. One source = one lead form on one platform. |
| `SocialLead` | A lead captured from a social platform. Stores contact info (name, email, phone, company, job title, LinkedIn URL), raw form data (JSON), and links to the auto-created FetchBot Lead. Tracks processing and voice call queueing status. |

## Supported Platforms

| Platform | Ingestion Method |
|---|---|
| Facebook Lead Ads | Webhook (hub.verify_token) |
| Instagram (via Facebook) | Webhook |
| LinkedIn Lead Gen Forms | Webhook / API polling |
| TikTok Lead Generation | API polling |
| X (Twitter) | API polling |
| Google Lead Form Extensions | API polling |

## Key Design Decisions

- **Platform-agnostic storage** — `SocialLead` has a normalized contact schema plus a `form_data` JSON field for platform-specific fields that don't fit the schema.
- **Deduplication** — `external_lead_id` prevents duplicate imports from webhook retries or polling overlaps.
- **Auto-promotion** — When `is_processed` flips to True, a FetchBot Lead is automatically created, bridging social ads into the main CRM pipeline.
- **Voice integration** — `voice_call_queued` flag enables automatic outbound AI voice calls to new social leads, connecting the social_leads and voice_agent apps.
- **Unique per form** — `unique_together = [("website", "platform", "form_id")]` ensures one source config per lead form.

## Dependencies

- **Depends on:** `websites`, `leads` (Lead creation), `analytics` (Visitor creation), `core`
- **Integrates with:** `voice_agent` (optional outbound calls to social leads)
- **External:** Facebook Graph API, LinkedIn Marketing API, TikTok Ads API, Google Ads API
