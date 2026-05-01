# LLM Ranking — Complete Technical & UX Reference

## Purpose

Measures how prominently a business appears in AI-generated answers across major LLMs (Claude, GPT-4, Gemini, Perplexity). This is **Generative Engine Optimization (GEO)** — understanding and improving your visibility when people ask AI assistants about your industry.

---

## What the Client Sees — Full UX Walkthrough

### 1. First Visit (No Audits)

When a user navigates to `/llm-ranking/:websiteId` and has never run an audit, they see:

- **`FirstRunLLMRanking` wizard** — a guided onboarding component that collects business name, industry, location, keywords, and optional context URLs. It shows a preview of the prompts that will be generated before the user commits.
- **"Set up your first audit" CTA** — if the wizard is dismissed, a card explains what the system does and offers a single button to start.

### 2. Running an Audit — What Happens When They Click "Run New Audit"

1. **Run Audit modal** opens → user can override business name, industry, location, keywords, select which LLM providers to query, and optionally paste extra URLs (blog posts, product pages) for context enrichment.
2. **POST to backend** → audit is created with status `pending`, Celery task is enqueued.
3. **Page enters live mode:**
   - **AI Visibility Score widget** shows a progress bar (`queries_completed / total_queries`) and a pulsing "Running" badge.
   - **Pipeline Log card** auto-expands — a terminal-style feed that auto-scrolls as log entries arrive:
     ```
     10:32:01  Starting audit for FetchBot (SaaS analytics)
     10:32:01  Selected LLM providers: Claude, GPT-4, Gemini, Perplexity
     10:32:02  🔍 Scanning main website: https://fetchbot.ai
     10:32:04  ✅ Website scanned — found 4 product(s)/service(s)
     10:32:05  🌐 Google Search: found 6 competitive snippet(s)
     10:32:06  📦 Context assembled — 3,412 chars of business intelligence
     10:32:06  🚀 Running 40 queries (10 prompts × 4 providers)
     10:32:07  ━━━ Querying Claude ━━━
     10:32:07  📤 → Claude: "What are the best SaaS analytics platforms?"
     10:32:09  📥 ← Claude responded (1,842 chars) — extracting mentions...
     10:32:10  🏆 FetchBot mentioned at rank #3 — sentiment: positive
     10:32:10     ↳ Competitors found: Mixpanel, Amplitude, Heap
     ```
   - **Live Results ticker** — as each query completes, a row appears showing provider, prompt, and result badge (Ranked #3 / Not mentioned / API error).
   - Frontend polls `GET /audits/<aid>/logs/?after=<ts>` every 2 seconds.

4. **Audit completes** → status flips to `completed`, dashboard populates.

### 3. Brand Overview Dashboard (After Completion)

When clicking on a completed audit or loading the page with completed audits, the client sees:

#### Filter Bar (top)
Three dropdown filters that update all dashboard widgets in real-time:
- **Platform filter** — "All Platforms" or a specific provider (Claude, GPT-4, etc.)
- **Time Range filter** — Last 7 days, 30 days, 90 days, All time
- **Topic filter** — "All Topics" or a specific prompt intent (Recommendation, Comparison, Use Case, etc.)

#### KPI Strip (4 cards)
| Card | What it shows | Tooltip |
|------|--------------|---------|
| **Brand Visibility** | `mention_rate`% — how often you appear across all queries | "How often you appear when AI assistants are asked about your category" |
| **Citation Share** | Your mentions / total brand mentions (you + competitors) | "Of all brand mentions across AI responses, the share that are you" |
| **Brand Ranking** | Your position vs competitors by visibility (e.g., #2 of 8) | "Your position vs other brands by visibility in this audit" |
| **Closest Competitor** | Avatar + name of the brand nearest to you in rankings | "The brand right above or below you in the rankings" |

#### Row 2: Competitor Visibility Chart + Rankings Table
- **Left (2/3 width):** Multi-line Chart.js chart showing visibility % over time for you and top competitors. Hovering shows exact values.
- **Right (1/3 width):** Ranked list of all brands (you + competitors) with rank number, colored avatar, name, "(You)" tag for your brand, and visibility %. Hovering a row highlights the corresponding line on the chart.

#### Row 3: Citation Share Trend + Top Sources
- **Left:** Line chart of your citation share % over historical audits.
- **Right:** Table of web pages that LLMs cited, with columns: #, Web Page (favicon + domain), Type (pill: blog/docs/review/etc.), Citations count. Sortable by citations or domain.

### 4. LLM Systems Dropdown

A collapsible bar showing which AI providers are configured:
- **Collapsed:** Shows green pills for configured providers (e.g., `● Claude  ● GPT-4  ● Gemini`) and a gray pill (`+2 unconfigured`).
- **Clicking expands:** Full list with status dot, provider name, model name, and state ("Enabled" or "API key missing").

### 5. AI Visibility Score Widget

Clickable bar with a mini SVG donut ring showing the overall score (0–100). Clicking expands:

- **Score Breakdown** — four horizontal factor bars (matches the formula in `compute_overall_score`):
  - Mention Rate (40pts) — colored green/yellow/red based on score
  - Rank Position (30pts)
  - Sentiment (20pts)
  - Provider Coverage (10pts)
- **Provider Breakdown grid** — one card per provider showing mention rate badge, avg rank, and queries succeeded/total.

### 6. Prompts Table

Grouped by intent type (Recommendation, Comparison, Use Case, etc.):

- **Topic header row** (clickable to expand/collapse):
  - Topic name, prompt count, avg visibility %, top performer icons (colored dots per provider: green=hit, yellow=partial, gray=miss), "See →" link.
- **Expanded prompt rows:**
  - Full prompt text, visibility %, per-provider result dots, status pill ("Prompt Ran" / "No Mention").
- **Provider filter dropdown** at top-right to show only one provider's results.

### 7. Detailed Findings (Expandable)

Click "Expand" to see every individual query result:
- **Summary stats bar:** Queries Sent, Mentions Found, Avg Rank, Unique Prompts.
- **Per-query cards:**
  - Provider badge, Rank badge (e.g., "Ranked #3"), Sentiment badge, Confidence %.
  - **Q:** the prompt that was asked.
  - **Match:** the snippet of text where your brand was found.
  - **`<details>` toggle:** "View full AI response (1,842 chars)" — click to see the raw LLM output.
  - Failed queries show provider, "API Failed" badge, and error message.

### 8. Recommendations Card

Auto-generated actionable advice based on audit results (e.g., "Your business is rarely mentioned by AI assistants. Publish detailed comparison articles..."). Numbered list.

### 9. How This Score Was Calculated

Expandable methodology card with 4 numbered steps:
1. Generate Prompts — shows count and business context used.
2. Query AI Providers — lists which providers were queried.
3. Analyze Responses — explains mention detection, rank extraction, sentiment classification.
4. Compute Score — shows the exact formula with point allocations.

### 10. Audit Jobs List

Historical audit runs in a compact expandable list:
- **Each row:** Date, business name, score pill (color-coded), mention rate %, query count, status badge.
- **Clicking a row expands** to show the prompt list with columns: #, Prompt text, Type badge, Provider dots, Result badge (Mentioned/No mention).
- **Run button** (▶) appears for pending/failed audits — clicking executes synchronously.
- **Delete button** (×) with confirmation.

### 11. Schedule Modal

"Schedule" button opens a modal to configure automatic recurring audits:
- Frequency: Weekly / Every 2 Weeks / Monthly
- Business context fields (pre-filled from website)
- Provider selection
- Enable/disable toggle

When active, a banner shows: "Auto-audit runs **weekly** — next run in 3 days" with a Disable button.

---

## Architecture

```
User triggers audit (or schedule auto-triggers)
  │
  ▼
LLMRankingAudit created (status: pending)
  │
  ▼
Celery Task (ai queue)
  │
  ├── Content Enrichment
  │     ├── Scan main website URL (domain_scanner)
  │     ├── Scan extra URLs in parallel (ThreadPoolExecutor, 3 workers)
  │     ├── Google Search for competitive context
  │     └── Build enriched system prompt for Claude
  │
  ├── Generate prompts
  │     ├── Load industry-matched prompt pack (JSON)
  │     ├── Intent-balanced sampling (recommendation, comparison, use_case, ...)
  │     └── Claude generates 4 additional natural-language variants
  │
  ├── For each (prompt × provider):
  │     ├── Query the LLM API
  │     ├── Extract structured data via Haiku (LLM-based extraction)
  │     │     ├── target_mentioned, target_position, target_linked
  │     │     ├── target_sentiment (positive/neutral/negative)
  │     │     ├── competitors_mentioned [{name, position, linked}]
  │     │     ├── primary_recommendation
  │     │     └── citations [URLs]
  │     ├── Falls back to heuristic regex analyzer on failure
  │     ├── Create LLMRankingResult
  │     └── Append to audit_logs (live pipeline feed)
  │
  └── Compute aggregate scores
        ├── overall_score (0-100)
        ├── mention_rate (% of queries with a mention + Wilson 95% CI)
        └── avg_mention_rank (average position when mentioned)
```

---

## Models

| Model | Purpose |
|---|---|
| `LLMRankingAudit` | A single audit run. Stores business context snapshot (name, description, industry, location, keywords, context_urls), prompts used, progress tracking, aggregate scores, and `audit_logs` (JSON array for live pipeline feed). |
| `LLMRankingResult` | One response from one LLM for one prompt. Captures `is_mentioned`, `mention_rank`, `sentiment`, `confidence_score`, `mention_context`, `is_linked`, `competitors_mentioned`, `primary_recommendation`, `citations`, `extraction_model`, `extraction_version`. |
| `LLMRankingSchedule` | Per-website periodic schedule. Stores business context, frequency (weekly/biweekly/monthly), and `next_run_at` for automatic audit creation via Celery Beat. |

---

## Service Layer

### `ranking_service.py` — `LLMRankingService`

| Method | What it does |
|---|---|
| `generate_prompts()` | Loads intent-balanced prompts from `PromptLibrary`, then asks Claude for 4 additional natural-language variants. Returns `[{text, type}]`, capped at 10. |
| `_query_claude()` | Calls `claude-sonnet-4-20250514` with enriched system prompt (includes scraped website data). |
| `_query_openai()` | Calls `gpt-4o-mini` via OpenAI SDK. |
| `_query_gemini()` | Calls `gemini-1.5-flash` via Google Generative AI SDK. |
| `_query_perplexity()` | Calls `llama-3.1-sonar-small-128k-online` via REST (web-grounded). |
| `_analyze_mention()` | Heuristic fallback — regex-based rank extraction from numbered lists, lexicon-based sentiment classification. |
| `compute_overall_score()` | Aggregates results into 0-100 score with Wilson CI on mention rate. |
| `run_audit()` | Main orchestrator — enrichment → prompts → per-provider queries → extraction → aggregation. Writes `audit_logs` after each step. |
| `generate_recommendations()` | Returns actionable advice based on mention rate, avg rank, missing providers, negative sentiment. |

### `extraction_service.py` — `HaikuExtractionService`

Uses `claude-haiku-4-5` to parse each raw LLM response into structured JSON:
```json
{
  "target_mentioned": true,
  "target_position": 3,
  "target_linked": false,
  "target_sentiment": "positive",
  "target_context": "FetchBot is a powerful analytics...",
  "competitors_mentioned": [
    {"name": "Mixpanel", "position": 1, "linked": true}
  ],
  "primary_recommendation": "Mixpanel",
  "citations": ["https://example.com/review"]
}
```
Falls back to heuristic `_analyze_mention()` if the Haiku call fails.

### `content_enricher.py` — `ContentEnricher`

Multi-source context aggregation for Claude's system prompt:
1. **Main website scan** — `domain_scanner.scan_domain()` extracts products, features, selling points.
2. **Extra URL scans** — parallel ThreadPoolExecutor (3 workers, max 5 URLs).
3. **Google Search** — queries `"{business} review"` and `"best {industry} tools {business}"`, extracts snippets and competitor names.
4. **Combined context** — assembles `=== MAIN WEBSITE ===`, `=== ADDITIONAL PAGES ===`, `=== WHAT GOOGLE SAYS ===` sections injected into Claude's system prompt.

### `prompt_library.py` — `PromptLibrary`

Intent-balanced prompt generation from JSON packs:

| Pack | File | Matches |
|---|---|---|
| Default | `prompt_packs/default.json` | Always loaded |
| SaaS | `prompt_packs/saas.json` | Industries containing "saas" |
| E-commerce | `prompt_packs/ecommerce.json` | "ecommerce", "e-commerce", "dtc" |
| Legal | `prompt_packs/legal.json` | "legal", "law", "attorney" |
| Agency | `prompt_packs/agency.json` | "agency", "marketing" |
| Healthcare | `prompt_packs/healthcare.json` | "health", "clinic", "telehealth" |

**Intent priority weights** (controls sampling):
```
recommendation: 2    comparison: 2     use_case: 2
alternatives:   1    category:   1     persona:  1
review:         1    local:      1 (only if location provided)
```

---

## Scoring Formula

```
Overall Score (0–100) =
  Mention Rate component (0–40 pts)
    = mention_rate% × 0.40

+ Rank Position component (0–30 pts)
    = avg_rank ≤ 1 → 30pts
    = avg_rank ≤ 3 → 20pts
    = avg_rank ≤ 5 → 15pts
    = avg_rank ≤ 10 → 10pts
    = avg_rank > 10 → 5pts

+ Sentiment component (0–20 pts)
    = (positive_count × 20 + neutral_count × 10) / mentioned_count

+ Provider Coverage bonus (0–10 pts)
    = 10pts if ≥ 3 providers succeeded, else (count/3 × 10)
```

**Mention Rate CI:** Wilson score interval at 95% confidence — stays sensible for small sample sizes (n < 30).

---

## Providers

| Provider | Model | Implementation | Status |
|---|---|---|---|
| `claude` | `claude-sonnet-4-20250514` | Anthropic SDK | ✅ Active |
| `gpt4` | `gpt-4o-mini` | OpenAI SDK | ✅ Active |
| `gemini` | `gemini-1.5-flash` | Google Generative AI SDK | ✅ Active |
| `perplexity` | `llama-3.1-sonar-small-128k-online` | REST API | ✅ Active |
| `meta_llama` | — | — | ⬜ Schema only |
| `mistral` | — | — | ⬜ Schema only |
| `cohere` | — | — | ⬜ Schema only |
| `deepseek` | — | — | ⬜ Schema only |
| `grok` | — | — | ⬜ Schema only |
| `amazon_nova` | — | — | ⬜ Schema only |

---

## Celery Tasks

Both run on the `ai` queue (isolated from default/integrations/webhooks).

| Task | Schedule | Purpose |
|---|---|---|
| `run_llm_ranking_audit` | On-demand | Execute a complete audit. `max_retries=1`, `countdown=30s`. |
| `dispatch_scheduled_audits` | Every 15 min (Beat) | Finds enabled schedules with `next_run_at <= now`, creates audits, enqueues tasks. |

---

## API Endpoints

All under `/api/v1/llm-ranking/`. All views enforce `IsAuthenticated` + tenant scoping via `TenantScopedAPIView`.

| Method | Path | View | What the UI does with it |
|---|---|---|---|
| GET | `<wid>/audits/` | `AuditListView` | Loads audit list for the Audit Jobs section |
| POST | `<wid>/audits/` | `AuditListView` | Creates + queues a new audit → returns 202 |
| GET | `<wid>/audits/<aid>/` | `AuditDetailView` | Loads full audit with all results for Detailed Findings |
| DELETE | `<wid>/audits/<aid>/` | `AuditDetailView` | Deletes an audit from the jobs list |
| POST | `<wid>/audits/<aid>/run/` | `AuditRunView` | Executes a pending/failed audit synchronously (dev mode) |
| GET | `<wid>/audits/<aid>/logs/` | `AuditLogsView` | Polled every 2s during running audit for Pipeline Log |
| GET | `<wid>/audits/<aid>/breakdown/` | `ProviderBreakdownView` | Populates the Provider Breakdown grid in the score widget |
| GET | `<wid>/audits/<aid>/recommendations/` | `RecommendationsView` | Loads the Recommendations card |
| GET | `<wid>/audits/<aid>/prompts/` | `PromptResultsView` | Populates the Prompts table (supports `?provider=` and `?type=` filters) |
| GET | `<wid>/audits/<aid>/providers/<p>/` | `ProviderDetailView` | Deep-dive report for a single provider |
| GET | `<wid>/preview-prompts/` | `PreviewPromptsView` | Shows prompts before committing to an audit (first-run wizard) |
| POST | `<wid>/scan-url/` | `ScanURLView` | Previews what will be extracted from a URL before adding it as context |
| GET | `<wid>/usage/` | `UsageView` | Token consumption, costs, call counts for the usage section |
| GET | `<wid>/history/` | `HistoryView` | Historical scores + per-provider + per-competitor stats for trend charts |
| GET | `<wid>/schedule/` | `ScheduleView` | Loads current schedule for the schedule modal |
| POST | `<wid>/schedule/` | `ScheduleView` | Creates/updates the schedule |
| DELETE | `<wid>/schedule/` | `ScheduleView` | Removes the schedule |

---

## Live Progress Flow

```
UI ──poll (2s)──> GET /audits/<aid>/logs/?after=<ts>
                    │
                    ▼
         AuditLogsView returns:
         {
           audit_id, status,
           queries_completed, total_queries,
           logs: [{ts, level, msg}, ...]
         }
                    ▲
                    │ append after each step
         Celery task (run_llm_ranking_audit)
           ├─ "Starting audit for FetchBot"              (info)
           ├─ "🔍 Scanning main website: ..."            (info)
           ├─ "✅ Website scanned — found 4 products"    (success)
           ├─ "🌐 Google Search: found 6 snippets"       (success)
           ├─ "🚀 Running 40 queries (10 × 4)"           (info)
           ├─ "📤 → Claude: "Best analytics...""         (info)
           ├─ "📥 ← Claude responded (1842 chars)"       (success)
           ├─ "🏆 FetchBot at rank #3 — positive"        (success)
           ├─ "❌ GPT-4 query failed: rate limit"        (error)
           └─ "🏁 AUDIT COMPLETE — Score: 73/100"        (success)
```

---

## Frontend Charts

| Chart | Library | Data Source | What it shows |
|---|---|---|---|
| Competitor Visibility | Chart.js `Line` | `/history/` → `competitors[]` per audit | Multi-line: visibility % over time for you + top competitors |
| Citation Share Trend | Chart.js `Line` | `/history/` → `citation_share` per audit | Your share of all brand citations over time |
| Provider Comparison | Chart.js `Bar` | `/breakdown/` | Mention rate per LLM provider (side-by-side bars) |
| Score Trend | Chart.js `Line` | `/history/` → `overall_score` per audit | AI visibility score over time |

---

## Dependencies

- **Internal:** `websites`, `accounts`, `core` (ai_tracking, permissions, tenant scoping)
- **External APIs:** Anthropic, OpenAI, Google Generative AI, Perplexity, Google Custom Search
- **Frontend:** Vue 3, Chart.js + vue-chartjs, axios
