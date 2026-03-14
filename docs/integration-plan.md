# GrowthPilot Integration Plan: Business-Justified Roadmap

## Context

GrowthPilot is an AI-powered growth intelligence SaaS (Django/DRF) that tracks website visitors via a pixel, scores leads, monitors competitors, runs website audits, and generates AI growth strategies. It monetizes via three tiers: Starter ($29/mo), Growth ($79/mo), Scale ($199/mo).

**The problem:** Codebase exploration reveals that nearly all external-facing data pipes are either stubs or dead-ends. The competitor module shows fake data. Hot lead alerts are coded but never called. The Integration model is a shell with no service logic. Users who pay for competitor tracking see empty dashboards. Users who configure Slack notifications never receive them. Leads are trapped inside the platform with no CRM handoff. This plan addresses the six most commercially damaging gaps.

---

## Integration 1: HubSpot CRM

### Business Case

**Codebase gap:** The lead lifecycle dead-ends inside GrowthPilot. `ScoringService.rescore_website()` (`apps/leads/services/scoring_service.py:59-63`) creates Lead objects when score >= 10, but when a lead goes hot (>= 70), absolutely nothing happens. `EmailService.send_hot_lead_alert()` and `SlackService.send_hot_lead_alert()` exist but are **never called anywhere**. `LeadService.update_status()` (`apps/leads/services/lead_service.py:30-34`) writes a status change and an audit log — zero side effects. The only export path is a manual CSV download via `LeadService.export_csv()`.

**Revenue impact:** HubSpot integration is the strongest driver for Starter-to-Growth upgrades. Users discover leads but can't act on them at scale. "Your leads are scored and waiting — connect HubSpot to close them" is a natural upsell prompt. CRM integration is the #1 feature cited in churn exit surveys for marketing analytics tools. Expected: 15-25% reduction in Growth-tier churn, 10-15% increase in Starter-to-Growth conversion.

**User pain:** Users generate leads via the pixel but must manually export CSV files, import into their CRM, and lose all behavioral context. By the time a sales rep contacts the lead, the data is stale.

**Competitive advantage:** Competing analytics tools (Hotjar, FullStory, Mouseflow) do NOT push leads to CRM. They are observation-only. GrowthPilot becomes the first pixel-to-pipeline platform for SMBs.

### Use Cases

1. **Auto-push hot leads:** When rescoring promotes a lead above threshold, automatically create a HubSpot contact with behavioral data (pages visited, time on site, source, company) and set lifecycle stage to "Marketing Qualified Lead."
2. **Bi-directional status sync:** Sales rep marks "Customer Won" in HubSpot → webhook updates `Lead.status` to `CUSTOMER` in GrowthPilot. And vice versa.
3. **Behavioral timeline in HubSpot:** Push `PageEvent` records as HubSpot timeline events so sales reps see "Visited pricing page 3 times" without leaving their CRM.
4. **Lead segment sync:** `LeadSegment` filter rules map to HubSpot active lists for consistent segmentation.
5. **Closed-loop attribution:** Lead converts in HubSpot → GrowthPilot attributes back to `Session.source`/`Session.campaign` for channel ROI.

### Architecture

```
ScoringService.rescore_website()
  → Lead.score >= threshold
    → sync_service.sync_lead_to_hubspot(lead)      [NEW]
      → hubspot_service.create_or_update_contact()  [HubSpot CRM v3 API]
      → hubspot_service.create_timeline_event()

HubSpot webhook POST /api/v1/integrations/hubspot/webhook/
  → webhooks.handle_hubspot_event()                 [Pattern from billing/webhooks.py]
    → sync_service.sync_from_hubspot(event_data)
      → LeadService.update_status()
```

- Extend `Integration.INTEGRATION_TYPES` (`apps/websites/models.py:74`) with `"hubspot"`
- Add `hubspot_contact_id` to `Lead` model
- Add `token_expires_at` to `Integration` model (needed for ALL OAuth integrations)
- New: `apps/integrations/services/hubspot_service.py`, `oauth_hubspot.py`, `sync_service.py`

### Choke Points

| Risk | Impact | Mitigation |
|------|--------|------------|
| HubSpot rate limit (100 req/10s) vs nightly bulk rescore | Leads don't sync | Batch API (`/batch/create`, 100 contacts/call). Celery `rate_limit='10/m'` |
| OAuth token expiry (6 hours) | Background tasks get 401s | Add `token_expires_at` to Integration model. Proactive refresh 15 min before expiry |
| Bi-directional sync loops | Infinite update cycles | `last_synced_from` field + 60s dedup window |
| Data mapping conflicts | Custom HubSpot properties don't match | JSON field for custom property mapping, sensible defaults |

### Monetization

- **Starter:** No CRM. CSV export only.
- **Growth ($79):** One-way push (auto-sync hot leads). Primary upgrade driver.
- **Scale ($199):** Bi-directional sync, custom field mapping, timeline events, segment sync.

---

## Integration 2: Google Ads

### Business Case

**Codebase gap:** The `Integration` model (`apps/websites/models.py:71-92`) supports `ga`, `gsc`, `facebook` types with encrypted token storage but **no service code exists** to use any of them. The analytics `Session` model tracks `source`, `medium`, `campaign` UTM parameters (`apps/analytics/models.py:49-51`) but there is zero way to correlate with ad spend. Users see "google / cpc" traffic but have no idea what it cost.

**Revenue impact:** Average SMB spends $1,000-$10,000/mo on Google Ads. A tool showing "this lead cost you $47 to acquire" directly justifies GrowthPilot's $79-$199/mo as a rounding error on ad spend. Projected: 8-12% new Growth signups from performance marketers.

**User pain:** Users run Google Ads campaigns driving traffic to their site. GrowthPilot tracks visitors and scores leads. But users cannot see "Campaign X generated 15 leads at $32 each." They must manually cross-reference Google Ads with GrowthPilot — most SMBs never do this, flying blind on spend.

**Competitive advantage:** GA provides aggregate conversion tracking but doesn't tie individual identified leads to specific ad spend. This capability typically requires HubSpot Marketing Hub ($800/mo) or Marketo. GrowthPilot delivers it at $79/mo.

### Use Cases

1. **Cost overlay on lead list:** Match `Session.campaign` UTM data with Google Ads campaign costs. New column: "Acquisition Cost: $34.50."
2. **ROAS dashboard:** Per-campaign: leads generated, conversions, return on ad spend.
3. **AI budget recommendations:** Feed ad performance into `StrategyGenerator._build_prompt()` (`apps/strategy/services/strategy_generator.py:58`) — "Increase Campaign X budget by 20%, it produces leads at $25 vs Campaign Y at $68."
4. **Competitor ad intelligence:** Auction Insights data feeds into `CompetitorSnapshot.metrics` JSON.
5. **Cost-per-lead alerts:** When CPA exceeds 2x average, trigger notification via existing `NotificationService`.

### Architecture

```
Daily Celery: sync_google_ads_data
  → google_ads_service.fetch_campaign_metrics(date_range)
    → Store in AdCampaignMetric model (campaign_id, cost, clicks, date)
  → For Sessions with source="google", medium="cpc":
    → Match Session.campaign → AdCampaignMetric
    → Update Lead.acquisition_cost (new field)
```

- Extend existing Google OAuth (`apps/accounts/services/oauth_service.py`) with `adwords` scope
- Add `google_ads` to `Integration.INTEGRATION_TYPES`
- New model: `AdCampaignMetric`, new field: `Lead.acquisition_cost`

### Choke Points

| Risk | Impact | Mitigation |
|------|--------|------------|
| Google Ads API complexity (GAQL, not REST) | Dev effort | Use `google-ads` Python library. Isolate in dedicated service |
| 15,000 ops/day quota (basic access) | Scales to ~5,000 websites | Aggregate campaign-level queries (1 req per account/day) |
| MCC multi-account tokens | Redundant API calls | `parent_integration` FK for shared credentials |
| 3-4 hour data lag | Morning brief missing yesterday's finals | Pull at 4 AM, document the lag |

### Monetization

- **Starter:** No Google Ads.
- **Growth ($79):** Campaign-level cost data + basic ROAS dashboard.
- **Scale ($199):** Per-lead attribution, AI budget recommendations, auction insights.

---

## Integration 3: Zapier / Outbound Webhooks

### Business Case

**Codebase gap:** This is the horizontal fix for Finding 1 (lead dead-ends) AND Finding 3 (integration shell). `LeadService.update_status()` produces only a DB write + audit log. `ChangeDetectionService.detect_changes()` creates records that go nowhere actionable. Audit completions update a status field and stop. Every event that should trigger downstream action is silently swallowed.

**Revenue impact:** Zapier compatibility is a checkbox for B2B SaaS purchasing decisions. Apps with Zapier integrations see 30% increase in trial-to-paid conversion (Zapier's own data). Additionally, this gives `api_access` (already in `PLAN_FEATURES["scale"]` at `core/permissions/rbac.py:20`) real value — currently it gates nothing useful.

**User pain:** A user on Pipedrive instead of HubSpot has zero automated lead handoff. A user on Microsoft Teams instead of Slack has zero notification path. Every user whose tool isn't specifically integrated is stuck with CSV export.

**Competitive advantage:** Transforms GrowthPilot from a standalone tool into a platform. The webhook infrastructure serves as foundation for all future integrations without building each one.

### Use Cases

1. **Hot lead to any CRM via Zapier:** Webhook fires → Zap creates contact in Pipedrive, Salesforce, Close, etc.
2. **Competitor change to any channel:** `CompetitorChange` creation fires webhook → user routes to Slack, Teams, email.
3. **Audit completion triggers:** Webhook with scores/issues → Notion entries, Trello cards, Asana tasks.
4. **Custom chains:** "Lead from US, score > 80, visited pricing → SMS via Twilio + Monday.com task."
5. **Data warehouse sync:** Scale users fire all events to BigQuery/Snowflake.

### Architecture

```
Service event (e.g., LeadService.update_status())
  → webhook_dispatch_service.dispatch(event_type, payload)
    → WebhookEndpoint.objects.filter(events__contains=[event_type], is_active=True)
    → For each: enqueue dispatch_webhook.delay(endpoint_id, payload, HMAC signature)
      → POST to url with X-GrowthPilot-Signature header
      → Retry: 3 attempts, exponential backoff (1s, 10s, 60s)
      → After 10 consecutive failures: disable endpoint, notify user
```

- New models: `WebhookEndpoint` (url, secret, events[], website FK), `WebhookDeliveryLog`
- Injection points: `ScoringService.rescore_website()`, `LeadService.update_status()`, `AuditOrchestrator`, `ChangeDetectionService.detect_changes()`
- Events: `lead.scored`, `lead.status_changed`, `lead.created`, `competitor.change_detected`, `audit.completed`, `visitor.identified`

### Choke Points

| Risk | Impact | Mitigation |
|------|--------|------------|
| Fan-out volume (10K leads rescored nightly) | Queue flood | Only emit `lead.scored` when score *crosses threshold*, not every rescore. Batch into single payload per endpoint |
| Dead endpoints blocking workers | Celery queue backup | Dedicated `webhooks` Celery queue. Auto-disable after 10 failures |
| SSRF via user-controlled URLs | Security vulnerability | Block private IP ranges, require HTTPS, HMAC-sign payloads |
| Payload size (unbounded JSON) | Memory issues | Cap at 256KB, include `detail_url` for full data |

### Monetization

- **Starter:** No webhooks.
- **Growth ($79):** 3 endpoints, `lead.*` events only.
- **Scale ($199):** Unlimited endpoints, all event types, delivery logs, custom headers.

---

## Integration 4: Semrush API

### Business Case

**Codebase gap:** This is an existential credibility problem. The entire competitor module is a facade. `CrawlService.crawl_competitor()` (`apps/competitors/services/crawl_service.py:11-25`) creates snapshots with `metrics={}`. Comment says "This would use DataForSEO, Ahrefs API, or similar." `DiscoveryService.auto_detect()` returns `[]`. Model fields `traffic_estimate`, `domain_authority`, `keyword_count`, `backlink_count`, `search_volume`, `difficulty` — all NULL in production. Demo seed data fills fake numbers to make the UI work. Settings `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD` (`config/settings/base.py:287-288`) exist but are never used in code.

**Why Semrush over DataForSEO:** (a) Stronger brand recognition — "powered by Semrush data" is a marketing asset, (b) more predictable API pricing, (c) more comprehensive competitive analysis endpoints. Implementation uses adapter pattern to allow swapping providers.

**Revenue impact:** Competitor tracking is a major Growth/Scale value prop (Growth: 10 competitors, Scale: 50). Without real data, these limits are meaningless — users pay for empty dashboards. Expected: 20-30% reduction in trial abandonment (users who add competitors and see zeroes currently churn), 5-10% Starter-to-Growth upgrade increase.

**User pain:** Users add competitors expecting traffic estimates, keyword rankings, backlink data. They see blanks. They lose trust in the platform's analytical capabilities, tainting perception of lead scoring and strategy features.

**Competitive advantage:** Most analytics tools (Hotjar, Crazy Egg, FullStory) provide zero competitor intelligence. "Analytics + intelligence" is genuinely differentiating.

### Use Cases

1. **Real competitor snapshots:** Replace stub in weekly `crawl_all_competitors` with Semrush Domain Overview API → populate `traffic_estimate`, `keyword_count`, `backlink_count`.
2. **Keyword gap analysis:** Semrush Keyword Gap endpoint → populate `KeywordGap` with real `search_volume`, `difficulty`, `opportunity_score`.
3. **Competitor auto-discovery:** Semrush Organic Competitors endpoint → replace empty `auto_detect()` with real suggestions.
4. **Trend-based threat detection:** Compare weekly snapshots. Traffic up 20% → create `CompetitorChange` with `change_type="ranking_change"` + notify.
5. **AI strategy enrichment:** Feed real competitor data into `StrategyGenerator._build_prompt()` — "Competitor ranks #3 for 'growth analytics' (vol: 2,400, diff: 45). Target with blog post."

### Architecture

```
Weekly Celery: crawl_all_competitors (Mon 1 AM, already scheduled)
  → CrawlService.crawl_competitor(competitor)
    → semrush_service.get_domain_overview(url)     [REPLACES empty stub]
      → Returns: traffic, keywords, backlinks, DA
    → CompetitorSnapshot.objects.create(real data)
    → semrush_service.get_keyword_gap(user, competitor)
      → Bulk upsert KeywordGap records
```

- New: `apps/integrations/services/semrush_service.py`, `competitor_data_adapter.py` (adapter pattern)
- Modified: `apps/competitors/services/crawl_service.py` (replace stub), `discovery_service.py` (replace empty return)

### Choke Points

| Risk | Impact | Mitigation |
|------|--------|------------|
| API unit cost ($0.01-0.05/request) | Cost explosion at scale | Cache 24h in Redis. Budget: Growth ~160 units/mo (~$2-5), Scale ~800 units/mo (~$8-20). Tier crawl frequency by threat level |
| Rate limit (10 req/sec) | Slow crawl | Dedicated Celery queue, `rate_limit='8/s'`. 1,000 competitors = ~2 min |
| Provider lock-in | Pricing changes | Adapter pattern. DataForSEO adapter as fallback (settings already exist) |
| Data freshness expectations | Users expect real-time | Show `last_crawled_at` prominently. Weekly is appropriate for SEO data |

### Monetization

- **Starter:** Manual competitor add, no data (just URL tracking). 3 competitor limit.
- **Growth ($79):** Real Semrush data, 10 competitors, weekly snapshots, keyword gaps, auto-discovery.
- **Scale ($199):** 50 competitors, on-demand refresh, historical trends, AI-enriched strategy.
- Marginal cost per Growth user: ~$2-5/mo. Well within margin on $79/mo plan.

---

## Integration 5: Slack App

### Business Case

**Codebase gap:** The current `SlackService` (`apps/notifications/services/slack_service.py`) is 37 lines sending plain text to a user-pasted webhook URL. `send_hot_lead_alert()` (line 26) **exists but is never called from anywhere**. `NotificationPreference.hot_lead_slack` and `slack_webhook_url` (`apps/notifications/models.py:39,43`) are never read by the scoring pipeline. Users who explicitly configure Slack notifications never receive them. This is a broken promise.

**Revenue impact:** Slack is a retention feature. Apps with interactive Slack integrations see 2x daily active usage vs dashboard-only products (Slack's data). Morning briefs, hot lead alerts, and competitor notifications surface in Slack, keeping GrowthPilot top-of-mind. Expected: 10-15% churn reduction for Growth/Scale users.

**User pain:** Users toggle `hot_lead_slack = True`, paste their webhook URL, and never receive a single message.

**Competitive advantage:** Command-driven workflows — `/growthpilot leads` to see hot leads, `/growthpilot audit` to trigger an audit, interactive buttons to change lead status from Slack. Moves from "dashboard you visit" to "assistant in your workspace."

### Use Cases

1. **Actually deliver hot lead alerts:** Wire existing dead code. Call `SlackService.send_hot_lead_alert()` from `ScoringService.rescore_website()`. Read `WebsiteSettings.notify_hot_leads`/`hot_lead_threshold`. This is a 1-2 day fix.
2. **Interactive lead management:** Block Kit buttons on alerts: "View Lead", "Mark Contacted", "Assign to Me." Clicks update `Lead.status` via callback.
3. **Morning brief in Slack:** Deliver the 6 AM brief (`morning_brief_service.py`) as a formatted Slack message.
4. **Slash commands:** `/growthpilot leads` → top 5 hot leads. `/growthpilot audit` → trigger audit. `/growthpilot competitors` → recent changes.
5. **Team channel routing:** Post to shared channels, not individual webhooks. Team sees assignments.

### Architecture

**Phase 1 (immediate — wire existing code):**
```
ScoringService.rescore_website()  [apps/leads/services/scoring_service.py:59-63]
  → After Lead.objects.update_or_create():
    → Check WebsiteSettings.notify_hot_leads & hot_lead_threshold
    → If score crossed threshold: call SlackService.send_hot_lead_alert()
    → Also call EmailService.send_hot_lead_alert()
```

**Phase 2 (full Slack app):**
```
Slack OAuth → store bot_token on Integration (type="slack")
Slash command → /api/v1/integrations/slack/commands/ → parse → respond
Button click → /api/v1/integrations/slack/interactions/ → LeadService.update_status()
```

### Choke Points

| Risk | Impact | Mitigation |
|------|--------|------------|
| 3-second response deadline | Slash commands timeout | Acknowledge immediately (200), dispatch work to Celery, respond via `response_url` |
| Slack app review (2-4 weeks) | Launch delay | Use restricted distribution during beta |
| Multiple workspaces per team | Token sprawl | One Slack workspace per Website (on Integration model) |
| Nightly rescore batch → rate limit (1 msg/sec/channel) | Messages dropped | Batch hot leads into single summary per channel per rescore |
| Migration from webhook | Break existing users | If Slack app connected, use it. If only webhook URL, keep legacy path |

### Monetization

- **Starter ($29):** Legacy webhook-only (but actually wired up so it works).
- **Growth ($79):** Full Slack app — rich notifications, interactive buttons, morning briefs.
- **Scale ($199):** Slash commands, team channel routing, custom notification rules.

---

## Integration 6: WordPress Plugin

### Business Case

**Codebase gap:** Pixel installation requires manually copying a JS snippet from `PixelService.get_snippet()` and pasting into HTML. For WordPress users (43% of all websites), this means editing theme files or using a header scripts plugin. Pixel verification (`PixelService.verify()`) only confirms installation after the user has already struggled through setup.

**Revenue impact:** The pixel is the foundation of all value — without it, no tracking, no leads, no analytics. Every user who fails to install churns before seeing value. WordPress plugin with one-click install could increase pixel completion rates 30-40% for WP users. If 40% of signups are WordPress and the plugin lifts activation from 60% to 85%, that's a 10% overall improvement in trial-to-paid.

**User pain:** Non-technical SMB owner sees "paste this JavaScript in your `<head>` tag," doesn't know what that means, and abandons setup.

**Competitive advantage:** GA, Hotjar, Clarity all have WordPress plugins. GrowthPilot's lack of one is a competitive gap that's easy to close.

### Use Cases

1. **One-click pixel install:** Install plugin → enter API key → pixel auto-injected via `wp_head` hook.
2. **Auto-verification:** Plugin calls GrowthPilot verification endpoint after activation.
3. **Form enrichment:** Hook into Contact Form 7, Gravity Forms, WPForms → capture `form_submit` events with email/name.
4. **WooCommerce tracking:** Purchase events and product page views for e-commerce attribution.
5. **Admin dashboard widget:** Key metrics (active leads, audit score) visible in WordPress admin.

### Architecture

- WordPress plugin (PHP, separate repo): `growthpilot.php`, settings page, pixel injector, form tracker
- Django side: `PluginVerifyView` endpoint for API key validation + pixel verification trigger
- Data flow: Plugin injects `<script>` with `pixel_key` → events flow through existing `EventIngestionService`

### Choke Points

| Risk | Impact | Mitigation |
|------|--------|------------|
| WordPress.org review (1-4 weeks) | Launch delay | Follow WP coding standards from day one |
| PHP 7.4-8.3 fragmentation | Compatibility issues | Target PHP 7.4+, test all versions |
| Caching plugin conflicts | Pixel blocked | Async script load from CDN, cache-busting docs |
| API key security (plaintext in wp_options) | Key leak if WP compromised | Scope keys to read-only + pixel verify only. Key rotation capability |

### Monetization

- **All tiers (free):** The plugin is an onboarding/activation tool, not a revenue gate. Gating it reduces activation. WordPress.org listing is a free distribution channel.

---

## Cross-Cutting Concerns

### Token Refresh (Systemic)
The `Integration` model has `access_token`/`refresh_token` but **no `token_expires_at`**. Every OAuth integration will fail silently during background Celery tasks.
- **Fix:** Add `token_expires_at = DateTimeField(null=True)` to Integration. Add `refresh_expiring_tokens` Celery beat task (every 15 min).

### Celery Queue Topology (Systemic)
Everything runs on the default queue. Slow external API calls block pixel aggregation.
- **Fix:** Split into queues: `default` (analytics, leads), `integrations` (HubSpot, Google Ads, Semrush), `webhooks` (outbound delivery), `ai` (strategy, briefs).

### Circuit Breaker Pattern
If Semrush goes down, every crawl task retries and backs up the queue.
- **Fix:** Redis-based circuit breaker: closed → open (after 5 failures, fail-fast 60s) → half-open (test 1 request).

### Updated PLAN_FEATURES
```python
# core/permissions/rbac.py
PLAN_FEATURES = {
    "starter": [..., "slack_webhook"],
    "growth":  [..., "hubspot_basic", "google_ads", "webhooks_basic",
                "competitor_intelligence", "slack_app"],
    "scale":   [..., "hubspot_advanced", "google_ads_advanced",
                "webhooks_advanced", "competitor_intelligence_advanced",
                "slack_advanced"],
}
```

---

## Implementation Sequence

| Phase | Weeks | Integration | Why This Order |
|-------|-------|-------------|----------------|
| 1a | 1-2 | Wire existing Slack/Email alerts | 1-2 day fix. Connects orphaned code. Immediate value |
| 1b | 1-2 | Zapier/Outbound Webhooks | Foundation for all integrations. Every future integration benefits |
| 2a | 3-5 | HubSpot CRM | Highest single-feature revenue impact |
| 2b | 3-4 | WordPress Plugin | Parallel (PHP). Onboarding lift |
| 3a | 6-7 | Semrush API | Fills competitor data gap. Makes existing models real |
| 3b | 6-8 | Slack App | Upgrades webhook → interactive app |
| 4 | 9-11 | Google Ads | Most complex OAuth. Benefits from prior infrastructure |

### Critical Files

| File | Role |
|------|------|
| `apps/leads/services/scoring_service.py` | Primary injection point — hot lead detection with no alerts/syncs |
| `apps/competitors/services/crawl_service.py` | Stub to replace with real Semrush data |
| `apps/competitors/services/discovery_service.py` | Stub returning empty list |
| `apps/websites/models.py` | Integration model shell + unused WebsiteSettings fields |
| `apps/notifications/services/slack_service.py` | Dead code to wire up |
| `apps/notifications/services/email_service.py` | Dead code to wire up |
| `core/permissions/rbac.py` | PLAN_FEATURES gating for all tiers |
| `apps/leads/services/lead_service.py` | Status updates with no side effects |
| `apps/strategy/services/strategy_generator.py` | Prompt enrichment with ad/competitor data |
| `config/celery.py` | Beat schedule + queue topology changes |

## Verification

1. **Slack/Email wiring:** Trigger rescore → verify hot lead notification delivered to Slack webhook and email
2. **Webhooks:** Create endpoint via API → trigger lead status change → verify POST received with valid HMAC signature
3. **HubSpot:** Connect OAuth → score lead above threshold → verify contact created in HubSpot sandbox
4. **Semrush:** Run competitor crawl → verify `CompetitorSnapshot` populated with real metrics (non-empty)
5. **Slack App:** Install app → trigger hot lead → verify Block Kit message with interactive buttons
6. **WordPress:** Install plugin on test WP site → verify pixel injected → verify `pixel_verified=True`
7. **Google Ads:** Connect OAuth → run daily sync → verify `AdCampaignMetric` records + `Lead.acquisition_cost` populated
8. **Cross-cutting:** Verify token refresh task runs. Verify circuit breaker trips on simulated API failure. Verify webhook queue isolated from default queue.
