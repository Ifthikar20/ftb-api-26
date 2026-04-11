# Websites App

## Purpose

The central entity in FetchBot. Every other app is scoped to a Website. This app manages website registration, pixel installation, team access (RBAC), external integrations (OAuth), and outbound webhooks.

## Architecture

```
User registers a website
  │
  ├── Website created with unique pixel_key
  │     └── User installs pixel on their site
  │           <script src="/pixel/growthpilot.min.js?key=<pixel_key>">
  │
  ├── Team Management
  │     WebsiteMembership (RBAC: owner/admin/editor/viewer)
  │
  ├── Integrations (OAuth)
  │     Integration model
  │       ├── Google Analytics / Search Console
  │       ├── Facebook Ads
  │       ├── Shopify
  │       ├── Mailchimp
  │       ├── Google Drive
  │       ├── Canva
  │       └── HubSpot
  │     Token lifecycle:
  │       ├── access_token + refresh_token (encrypted at rest)
  │       ├── token_expires_at
  │       ├── needs_token_refresh() — 15-min buffer
  │       └── Celery: refresh_expiring_tokens (every 15 min)
  │
  └── Webhooks (outbound)
        WebhookEndpoint
          ├── URL + HMAC-SHA256 signing secret (encrypted)
          ├── Event subscriptions (lead.scored, competitor.change_detected, etc.)
          └── Celery: deliver_webhook (webhooks queue)
```

## Models

| Model | Purpose |
|---|---|
| `Website` | Core entity. Stores URL, name, industry, pixel_key (UUID), pixel verification status, platform type (Shopify/WordPress/WooCommerce/Custom), and crawl status. Supports soft delete. |
| `WebsiteSettings` | 1:1 settings: anonymous tracking toggle, hot lead notifications, lead score threshold, weekly report opt-in. |
| `WebsiteMembership` | Team access with roles: owner, admin, editor, viewer. Tracks inviter and acceptance status. |
| `WebhookEndpoint` | Outbound webhook configuration with URL, event subscriptions, encrypted signing secret, activity tracking, and failure counter. |
| `Integration` | External service connection with encrypted OAuth tokens, expiry tracking, and auto-refresh. Supports 8 platform types. |

## Webhook Events

Endpoints can subscribe to any combination of:

| Event | Fired When |
|---|---|
| `lead.scored` | Lead score changes |
| `lead.status_changed` | Lead moves through pipeline |
| `lead.created` | New lead created |
| `competitor.change_detected` | Competitor crawl finds changes |
| `audit.completed` | LLM ranking audit finishes |
| `visitor.identified` | Anonymous visitor identified |
| `campaign.sent` | Email campaign sent |
| `link.clicked` | Tracked link clicked |

## Celery Tasks

| Task | Schedule | Queue | Purpose |
|---|---|---|---|
| `refresh_expiring_tokens` | Every 15 min | integrations | Refresh OAuth tokens expiring within 15 minutes |
| `deliver_webhook` | On-demand | webhooks | Deliver outbound webhook with HMAC signing |

## Key Design Decisions

- **Pixel-based tracking** — Each website gets a unique `pixel_key` (UUID). The pixel JS snippet uses this to identify which website the events belong to.
- **Encrypted at rest** — OAuth tokens (`access_token`, `refresh_token`) and webhook secrets use `EncryptedTextField` for security.
- **Proactive token refresh** — Tokens are refreshed 15 minutes before expiry via Celery beat, preventing integration outages.
- **Soft delete** — Websites use `SoftDeleteMixin` for safe deletion with recovery option.
- **Queue isolation** — Webhook delivery runs on a dedicated `webhooks` queue, and integration tasks on `integrations`, to prevent slow third-party calls from blocking the default queue.

## Dependencies

- **Depends on:** `accounts`, `core` (encryption, soft delete, constants)
- **Depended on by:** Every other app (ForeignKey to Website)
