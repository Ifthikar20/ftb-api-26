# Changelog

All significant changes made across this development session.

---

## Feature Removals

### Strategies App
- Removed `apps/strategy/` entirely — models, views, services, prompts, migrations
- Removed `apps/strategy.api.v1.urls` from `config/urls.py`
- Removed `/strategy/:websiteId` route from Vue Router
- Removed Strategy nav link from `AppLayout.vue` sidebar
- Removed `frontend/src/pages/StrategyPage.vue`
- Removed `frontend/src/api/strategy.js`
- Removed `apps.strategy` from `LOCAL_APPS` in `config/settings/base.py`

### Gamification / Rewards App
- Removed `apps/gamification/` entirely — models, views, migrations, management commands
- Removed `apps/gamification.urls` from `config/urls.py`
- Removed `/rewards` route from Vue Router
- Removed Rewards nav link from `AppLayout.vue` sidebar
- Removed gamification points badge from topbar (`<router-link to="/rewards" class="points-badge">`)
- Removed `userPoints`, `userLevel` refs and `progress()` fetch from `AppLayout.vue`
- Removed `frontend/src/pages/RewardsPage.vue`
- Removed `frontend/src/api/gamification.js`
- Removed `frontend/src/components/gamification/CollectibleCard.vue`
- Removed `GAMIFICATION_ENABLED` setting from `config/settings/base.py`
- Removed `apps.gamification` from `LOCAL_APPS`

### Audits App
- Removed `apps/audits/` entirely — models, views, services, migrations
- Removed `apps.audits.api.v1.urls` from `config/urls.py`
- Removed `/audits/:websiteId` route from Vue Router
- Removed Audits nav link from `AppLayout.vue` sidebar
- Removed `frontend/src/pages/AuditsPage.vue`
- Removed `frontend/src/api/audits.js`
- Removed `apps.audits` from `LOCAL_APPS`
- Removed audits onboarding step from `AppLayout.vue`

---

## Voice Agent

### Documentation
- Created `docs/voice-agent.md` — 11-section guide covering:
  - Architecture diagram
  - Phone number setup (E.164 format, SIP/PSTN)
  - 8-step call handling flow
  - Agent context documents and system prompt assembly
  - Post-call extraction pipeline with full JSON schema
  - Social media integration per platform
  - All 3 deployment backends (Retell AI, LiveKit, self-hosted)
  - Webhook reference with all event payloads
  - Configuration field reference and cost comparison table

### New Models (`apps/voice_agent/models.py`)
- `PhoneNumber` — stores work phone numbers per website in E.164 format; tracks provider (Telnyx), active state, and forwarding flag
- `AgentContextDocument` — Markdown knowledge base documents injected into the LLM system prompt at call time; supports ordering and active/inactive toggle

### Migration
- `apps/voice_agent/migrations/0002_phonenumber_agentcontextdocument.py`

### New API Endpoints (`apps/voice_agent/api/v1/`)
- `GET/POST /<website_id>/phone-numbers/` — list and add phone numbers
- `PUT/DELETE /<website_id>/phone-numbers/<number_id>/` — update or remove a number
- `GET/POST /<website_id>/context-docs/` — list and create context documents
- `PUT/DELETE /<website_id>/context-docs/<doc_id>/` — update or remove a document

### Serializers
- `PhoneNumberSerializer`
- `AgentContextDocumentSerializer`

### Frontend (`frontend/src/api/voiceAgent.js`)
Added methods:
- `getPhoneNumbers`, `addPhoneNumber`, `updatePhoneNumber`, `deletePhoneNumber`
- `getContextDocs`, `createContextDoc`, `updateContextDoc`, `deleteContextDoc`

### Frontend (`frontend/src/pages/VoiceAgentPage.vue`)
- Added **Phone Numbers** tab — table with add/edit/delete, forwarding instructions card
- Added **Social Leads** tab — connected platforms grid, LinkedIn sync, Facebook webhook info, X JSON import
- Added **Knowledge Base** section inside Settings tab with document editor
- New modals for phone number CRUD, context document CRUD, social platform connection

---

## Social Leads Integration

### New App (`apps/social_leads/`)
Full Django app created from scratch.

**Models (`models.py`)**
- `SocialLeadSource` — platform configuration (Facebook, LinkedIn, X/Twitter, TikTok, Instagram, Other) with OAuth tokens, webhook secrets, sync scheduling
- `SocialLead` — individual imported leads with platform-native ID, name, email, phone, company, campaign source, status, and raw payload

**Services (`services/lead_processor.py`)**
- `LeadProcessor` — base class
- `FacebookLeadService` — HMAC-SHA256 webhook verification, Graph API lead data retrieval
- `LinkedInLeadService` — polling-based sync (LinkedIn has no webhooks)
- `XLeadService` — CSV import handler

**API Views (`api/v1/views.py`)**
- `SocialLeadSourceListView` / `SocialLeadSourceDetailView` — CRUD for platform configs
- `SocialLeadListView` — list leads with platform filter
- `FacebookWebhookView` — receives and verifies Facebook Lead Ads webhooks
- `LinkedInSyncView` — triggers a manual LinkedIn poll
- `XCSVImportView` — imports leads from uploaded CSV

**Routes (`api/v1/urls.py`)**
- `api/v1/social-leads/` registered in `config/urls.py`

**Settings (`config/settings/base.py`)**
```
FACEBOOK_APP_ID, FACEBOOK_APP_SECRET
LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET
TIKTOK_APP_ID, TIKTOK_APP_SECRET
```

**Frontend (`frontend/src/api/socialLeads.js`)**
- `getSources`, `createSource`, `updateSource`, `deleteSource`
- `getLeads`, `syncLinkedIn`, `importX`

---

## Keyword Intelligence

### New Models (`apps/analytics/models.py`)

#### `KeywordScanConfig`
Per-website automatic DOM scan schedule.
- `is_auto_scan_enabled` — toggle
- `scan_interval_hours` — 1 / 6 / 24 / 168
- `scan_depth` — max pages per crawl (1–20)
- `last_scanned_at`, `next_scan_at`, `total_scans`

#### `PlatformContent`
Social platform posts stored for keyword comparison.
- `platform` — linkedin / x / facebook / instagram / blog / other
- `title`, `content`, `url`, `published_at`
- `extracted_keywords` (JSONField) — auto-populated on save via `extract_keywords_from_content()`
- `platform_post_id` — deduplication key

#### `KeywordAlert`
Alert rule that fires when a tracked keyword moves beyond a threshold.
- `tracked_keyword` (nullable FK) — null = applies to all keywords for the website
- `threshold` — minimum position change to trigger
- `direction` — any / improved / declined
- `notification_method` — email / in_app
- `is_active`, `last_triggered_at`

#### `KeywordAlertEvent`
Immutable log of every alert firing.
- `keyword`, `old_rank`, `new_rank`, `change`, `triggered_at`

#### `CompetitorDomain`
A competitor domain to track alongside the website's own keywords.
- `domain`, `name`, `is_active`, `last_checked_at`
- Unique together: `(website, domain)`

#### `CompetitorKeywordRank`
Point-in-time rank snapshot for a competitor.
- `competitor` (FK), `keyword`, `rank`, `checked_at`

### Migrations
- `0005_keywordscanconfig_platformcontent.py`
- `0006_keywordalert_keywordalertevent_competitordomain_competitorkeywordrank.py`

### New API Endpoints (`apps/analytics/api/v1/`)

#### Scan Schedule
- `GET/PUT /<website_id>/keywords/scan-config/` — read and update DOM scan schedule

#### Platform Content
- `GET/POST /<website_id>/keywords/platform-content/` — list and add platform posts
- `DELETE /<website_id>/keywords/platform-content/<post_id>/` — remove a post

#### Keyword Comparison
- `GET /<website_id>/keywords/comparison/` — overlap / gaps / opportunities analysis
- `GET /<website_id>/keywords/comparison/export/?format=csv` — CSV download
- `GET /<website_id>/keywords/comparison/export/?format=html` — printable HTML report

#### Keyword Alerts
- `GET/POST /<website_id>/keywords/alerts/` — list and create alert rules
- `PATCH/DELETE /<website_id>/keywords/alerts/<alert_id>/` — update or delete a rule
- `GET /<website_id>/keywords/alerts/events/` — list recent trigger events (last 50)

#### Competitors
- `GET/POST /<website_id>/competitors/` — list and add competitor domains
- `GET/DELETE /<website_id>/competitors/<competitor_id>/` — detail and remove
- `POST /<website_id>/competitors/<competitor_id>/refresh/` — queue a DataForSEO rank check
- `GET /<website_id>/competitors/overlap/` — side-by-side keyword rank comparison

### Celery Tasks (`apps/analytics/tasks.py`)

#### `check_keyword_alerts`
Runs on schedule. For every active `KeywordAlert`:
1. Fetches associated `TrackedKeyword` records
2. Computes `change = previous_rank - current_rank` (positive = improved)
3. Checks threshold and direction filters
4. Creates a `KeywordAlertEvent` on match
5. Sends email via SendGrid if `notification_method = email`

#### `check_competitor_rankings`
Triggered per competitor domain:
1. Fetches all tracked keywords for the parent website
2. Calls `DataForSEOService.enrich_keywords()` with the competitor domain
3. Stores a `CompetitorKeywordRank` snapshot per keyword
4. Updates `CompetitorDomain.last_checked_at`

### Frontend API (`frontend/src/api/analytics.js`)
New methods added:
```
getScanConfig, updateScanConfig
getPlatformContent, addPlatformContent, deletePlatformContent
keywordComparison, exportComparison
getAlerts, createAlert, updateAlert, deleteAlert, getAlertEvents
getCompetitors, addCompetitor, deleteCompetitor, getCompetitorDetail,
refreshCompetitor, getCompetitorOverlap
```

### Frontend Cards (`frontend/src/pages/KeywordsPage.vue`)

All new cards are added to the card picker system — users toggle them on/off individually and preferences persist in `localStorage`.

#### DOM Scan Schedule (`scan_schedule`)
- Auto-scan toggle (custom CSS switch)
- Interval picker: Hourly / Every 6h / Daily / Weekly
- Max pages slider (1–20)
- Last scanned and next scan timestamps

#### Platform Comparison (`platform_comparison`)
- Add posts from LinkedIn, X, Facebook, Instagram, Blog, or Other
- Platform filter dropdown
- Run comparison to see Overlap / Gaps / Opportunities tabs
- Export as CSV or printable HTML report

#### Keyword Alerts (`keyword_alerts`)
- **New rule** button slides open an inline form without a modal overlay
- Threshold stepper (+/- buttons)
- Direction and notification method as pill toggles
- Active rules list — each row shows keyword, threshold badge, direction badge, notification badge
- Custom CSS toggle switch per rule (enable/disable)
- Recent trigger events feed — up/down icon, keyword, rank delta (`#old → #new`), timestamp
- Bell icon shows animated red pulse dot when events exist
- Empty state with centered icon

#### Competitor Tracking (`competitor_tracking`)
- Domain list with favicon (Google S2), name, domain, last-checked time
- Refresh button with spin animation while DataForSEO check is queued
- "Compare rankings" button loads side-by-side table on demand
- Table shows `ahead / behind / tied` delta per competitor per keyword
- Empty state consistent with other cards

#### Historical Rank Charts (`history_charts`)
- Full-width card (spans both grid columns)
- Keyword selector chips — each adopts the matching line color when selected, shows current rank
- SVG line chart with area fill, dashed grid lines, rank #1 line highlighted in brand color
- Hover tooltip on data points: keyword, rank, date
- Color-coded legend with current rank per keyword
- Skeleton loading animation while fetching history data
- Up to 5 keywords charted simultaneously, last 30 days of `KeywordRankHistory`

---

## Bug Fixes

### `KeywordsPage.vue`
- **Vue 3 `v-if` + `v-for` on same element** (Site Audit score breakdown, line 47): In Vue 3, `v-if` has higher priority than `v-for`, meaning the loop variable `comp` was undefined when `v-if` evaluated. Fixed by wrapping with `<template v-for>` so iteration runs before the conditional check.
- **Dead function `cleanUrl`**: Defined but never called in the template. Removed.
- **Dead function `diffClass`**: Defined but never called in the template. Removed.
- **Missing `.ct-refreshing` CSS rule**: The Competitor Tracking refresh button applied this class via `:class` binding during loading state, but no style rule existed. Added `opacity: 0.7; pointer-events: none`.

### `apps/analytics/tasks.py`
- **N+1 query in `check_keyword_alerts`**: `alert.website.user` was accessed inside the loop to send email, causing a separate SQL query per alert. Fixed by adding `"website__user"` to `select_related`.

---

## Settings Changes (`config/settings/base.py`)

### Removed
- `apps.audits`, `apps.strategy`, `apps.gamification` from `LOCAL_APPS`
- `GAMIFICATION_ENABLED`

### Added
- `apps.social_leads` to `LOCAL_APPS`
- `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`
- `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`
- `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET`

---

## URL Routing (`config/urls.py`)

### Removed
- `apps.audits.api.v1.urls`
- `apps.strategy.api.v1.urls`
- `apps.gamification.urls`

### Added
- `api/v1/social-leads/` → `apps.social_leads.api.v1.urls`

---

## Navigation (`frontend/src/layouts/AppLayout.vue`)

### Removed
- Audits sidebar link
- Strategy sidebar link
- Rewards sidebar link
- Gamification points badge from topbar
- `import gamificationApi` import
- `userPoints`, `userLevel` reactive refs
- Gamification `progress()` call from `onMounted`
- `auditsRoute`, `strategyRoute` computed properties
- Audits and strategy entries from `searchPages` array and `switchWebsite` routeMap
- Audits onboarding step
- `.points-badge` CSS block

---

## Branch

All changes committed and pushed to `claude/remove-features-cleanup-8TCru`.
