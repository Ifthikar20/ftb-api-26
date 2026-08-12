# FetchBot Architecture

Companion documents: `docs/INFRASTRUCTURE.md` (what runs in production, capacity,
inspection recipes) and `DEPLOY.md` (release flow). Per-app design notes live in
`apps/<app>/ARCHITECTURE.md`.

---

## 1. System overview

FetchBot is a Django SaaS that measures and improves how a brand appears in answers
from large language models. The flagship feature is the **LLM Ranking Audit**: given a
business profile, the system asks several LLMs the kinds of questions a buyer would
ask, parses the answers, and scores brand visibility, citation share, sentiment and
competitive ranking over time.

```
┌────────────────────────────────────────────────────────────────────┐
│                   Cloudflare (Full Strict TLS)                     │
└────────────────────────────────────────────────────────────────────┘
                                  │
┌────────────────────────────────────────────────────────────────────┐
│                     EC2 (Ubuntu 22.04, t3.small)                   │
│                                                                    │
│   nginx ─┬──> /api/*  ──> web (Django + Gunicorn)                  │
│          ├──> /ws/*   ──> web (Channels)                           │
│          └──> /       ──> frontend (ftb-ui build artifact)         │
│                                                                    │
│   web ──┬──> Postgres 16  (all application data)                   │
│         ├──> Redis        (cache + Channels layer + Celery broker) │
│         └──> Celery worker + beat                                  │
│                       │                                            │
│                       ├──> Anthropic / OpenAI / Google /           │
│                       │    Perplexity / xAI APIs                   │
│                       └──> intelligence, sources (internal only)   │
└────────────────────────────────────────────────────────────────────┘
```

Nine containers in `docker/docker-compose.prod.yml`:

| Service | Memory cap | Source |
|---|---|---|
| `db` | 300M | `postgres:16-alpine` |
| `redis` | 150M | `redis:7-alpine` |
| `web` | 500M | built from `docker/Dockerfile` (Gunicorn, 2 sync workers) |
| `celery` | 400M | built from `docker/Dockerfile.celery` (worker + beat in one container) |
| `frontend` | — | pulled image `ghcr.io/ifthikar20/ftb-ui:${UI_VERSION:-latest}`, exports `dist` into a volume |
| `nginx` | 50M | `nginx:alpine`, TLS termination, mounts certs from `/opt/fetchbot/ssl` |
| `intelligence` | 150M | built from `services/intelligence/Dockerfile` (FastAPI, internal only) |
| `sources` | 150M | built from `services/sources/Dockerfile` (FastAPI, internal only) |
| `openclaw` | 400M | disabled — `restart: "no"` |

With `openclaw` disabled the active limits total roughly 1.7 GB against a 2 GB
instance. A swapfile is assumed; `scripts/deploy.sh` warns when none is active but
does not create one.

---

## 2. The UI is a separate repository

The Vue 3 frontend lives in **`ftb-ui`** and is built and published by its own GitHub
Action as `ghcr.io/ifthikar20/ftb-ui`. Production pulls that image; nothing in this
repository builds it. The `frontend/` directory here is a leftover Vite cache.

The contract the UI depends on, all defined in `core/`:

- **Auth** — JWT bearer, `Authorization: Bearer <access>`. Access tokens last 7 days,
  refresh tokens 60 days with rotation and blacklisting. The access token is returned
  in the response body; the refresh token is set as an httpOnly cookie by
  `apps/accounts/api/v1/views.py`, and `POST /api/v1/auth/refresh/` reads it from
  there.
- **Response envelope** — `core/interceptors/response_envelope.py` wraps every 2xx as
  `{"success": true, "data": ..., "meta": {...}}`. Paginated responses move
  `count`/`next`/`previous` into `meta`, along with any extra top-level keys a view
  attached.
- **Errors** — `core/interceptors/exception_handler.py` returns
  `{"success": false, "error": {"code", "message"}, "request_id"}`. Internal exception
  text is logged server-side and never returned.
- **Pagination** — `core/interceptors/pagination.py::StandardPagination`, 25 per page,
  max 100.
- **Correlation** — `core.middleware.request_id` stamps a request ID that appears in
  logs and in every error body.
- **Schema** — OpenAPI at `/api/schema/`, Swagger UI at `/api/schema/swagger/`,
  ReDoc at `/api/schema/redoc/`.

---

## 3. Request handling

### Tenant scoping

`Website` (`apps/websites/models.py`) is the tenant root. Almost every other model
hangs off it. Isolation is centralized rather than repeated per view:
`core/views/base.py::TenantScopedAPIView` sets `permission_classes = [IsAuthenticated]`
and exposes `get_website()`, which resolves the `website_id` URL kwarg through
`WebsiteService.get_for_user()`. That helper raises `ResourceNotFound` — a 404, never
a 403 — so object IDs cannot be probed. `TenantScopedListAPIView` adds
`paginated_response()`.

New endpoints should extend these bases rather than hand-rolling the ownership check.

### Middleware chain

Order matters; see `config/settings/base.py`. Request ID and security headers first,
then the billing webhook rate limiter, CORS, request sanitization, auth, audit
logging, the adaptive rate limiter, django-axes, and structlog correlation last.

### Throttling

`core/interceptors/throttling.py`: burst 500/min and sustained 20000/hour globally,
plus `AuthRateThrottle` (60/min), `PasswordResetThrottle` (3/hour),
`AIGenerationThrottle` (10/hour), and `PixelIngestThrottle` (10000/min, keyed on
`pixel_key` rather than IP).

### Unauthenticated surface

`/health/`, `/api/v1/version/`, the AllowAny endpoints under `/api/v1/auth/`,
`/api/v1/track/event|batch/` (authenticated by `pixel_key` in the payload),
`/t/<tracking_key>/`, `/api/v1/billing/webhook/` (Stripe signature),
`/api/v1/billing/health/`, `/api/v1/search-console/oauth/callback/` (signed `state`),
and the analytics SEO script views.

---

## 4. The LLM Ranking pipeline

### Data model — `apps/llm_ranking/models.py`

- **`LLMRankingAudit`** — one audit run. Snapshots the business context
  (`business_name`, `industry`, `location`, `keywords`, `description`, `context_urls`)
  so historical runs stay interpretable. Status `pending → running → completed |
  failed`. Aggregates: `overall_score` (0-100), `mention_rate` with Wilson 95%
  confidence bounds, `mention_rate_smoothed` (Beta-Binomial), `avg_mention_rank`,
  `brand_strengths` (Plackett-Luce). Progress: `queries_completed` / `total_queries`.
  `audit_logs` is a JSON array of `{ts, level, msg}` that the UI polls for live
  progress. `prompt_source` records whether prompts came from the vault, the library,
  or both.
- **`LLMRankingResult`** — one (prompt x provider) cell. Carries `response_text`,
  `is_mentioned`, `mention_rank`, `sentiment`, `confidence_score`, `is_linked`,
  `competitors_mentioned`, `citations`, `primary_recommendation`, plus provenance
  (`extraction_model`, `extraction_version`, `run_id`). A `public_id` UUID gives the
  UI a non-enumerable external identifier.

  The unique constraint on `(audit, prompt_index, provider, run_id)` is the
  idempotency key: a retried cell task upserts instead of duplicating.
- **`LLMRankingSchedule`** — periodic audits. Frequency, `next_run_at`,
  `consecutive_failures` and `auto_pause_threshold` so a persistently failing schedule
  disables itself.
- **`ModelTestRun`** — durable archive of ad-hoc multi-model probes, with
  `to_state_dict()` to replay the live-poll shape after the Redis TTL expires.

### Providers — `apps/llm_ranking/providers/`

`base.py::LLMProvider` owns the circuit breaker, token bucket, timing, error
normalization into `ProviderResult`, and the mandatory write to `AITokenUsage`.
Subclasses implement only `_call()`. This is deliberate: adding a provider cannot
silently skip cost tracking.

Two registries in `providers/__init__.py`:

- **`PROVIDERS`** — selectable for real audits: `claude`, `gpt4`, `gemini`,
  `perplexity`, `grok`.
- **`TOOLING_PROVIDERS`** — cheap synthesis only: `deepseek`, `claude`, `gpt4`.
  DeepSeek is intentionally absent from `PROVIDERS` so the audit router can never
  select it. Use `get_synthesis_provider()`, which reads
  `settings.PROMPT_SYNTHESIS_PROVIDER` and falls back along the tooling chain.

`MODEL_VARIANTS` maps each provider to its selectable models and drives the Model Test
picker. Removing a variant does not break historical runs — results store the model id
verbatim.

### Prompt sourcing — `apps/llm_ranking/services/audit_runner.py`

`apply_to_audit(audit, prompt_source=...)` resolves the final prompt list from the
brand vault (`_from_vault`), a prompt-library sample (`_from_library_sample`), or a
hybrid of both, and writes it onto the audit. `gather_prompts()` is the read-only
equivalent used by preview endpoints.

### Orchestration — `apps/llm_ranking/tasks.py`

1. `run_llm_ranking_audit(audit_id)` calls `LLMRankingService.prepare_audit()`, which
   validates providers and prompts, runs `ContentEnricher.enrich()`, flips the audit
   to `running`, snapshots `total_queries`, ingests the enrichment back into the RAG
   knowledge base, and runs the `business_story` DOM scan.
2. It then fans out a **Celery chord** — one `query_provider_prompt_task` per
   (prompt x provider) cell onto the `ai` queue.
3. Each cell runs `LLMRankingService.run_audit_cell()`: restore enriched context,
   per-prompt RAG retrieval, build the system prompt, call the provider (breaker,
   rate limit and cost recording applied by the base class), extract mentions, then
   `update_or_create` against the unique constraint. It dispatches citation extraction
   fire-and-forget and atomically increments `queries_completed` with an `F()` update,
   which is what drives the live progress bar and ETA.
4. The chord callback `aggregate_audit_results_task` calls `finalise_audit()`, which
   computes the aggregate scores, rolls up token cost, and marks the audit completed.

`dispatch_scheduled_audits()` runs every 15 minutes from Celery beat, finds enabled
schedules whose `next_run_at` has passed, creates and enqueues the audit, and advances
the schedule.

For local debugging, `LLM_SCAN_MODE` switches between the chord and an in-thread
inline run (`run_audit_sync()`), and dev settings set `CELERY_TASK_ALWAYS_EAGER`.

### Live progress

```
UI ──poll──> GET /audits/<aid>/logs/?after=<ts>
              │
              ▼
     LLMRankingAuditLogsView returns audit.audit_logs
              ▲
              │ append
   Celery cell tasks
     ├─ "Starting audit for FetchBot"        (info)
     ├─ "Generated 8 prompts"                (info)
     ├─ "Claude query 1/8 succeeded (842ms)" (success)
     ├─ "OpenAI query 2/8 failed: rate limit"(warn)
     └─ "Audit completed: score 73"          (success)
```

---

## 5. Cost governance

Every LLM call funnels through `core/ai_tracking.py::record_usage()`, which writes one
`AITokenUsage` row capturing module, provider, model, input/output tokens,
`duration_ms`, `estimated_cost_usd` from a per-model price table, plus user, website
and free-form metadata. `get_usage_summary()` rolls that up by module, model, provider
and day; `month_to_date_cost()` powers the per-user spend cap.

Three layers of protection:

1. **Per-user monthly spend cap** — `User.monthly_ai_cost_cap_usd`. Checked before an
   audit is created and again inside the task; exceeding it returns **HTTP 402**.
2. **Per-user daily API budgets** — `core/quota.py::DailyQuota`, a Redis-backed counter
   with a 26-hour TTL, one namespace per feature (Google CSE, the Claude judge, GEO
   rewrite, Perplexity search, GSC).
3. **Circuit breakers and token buckets** — `core/resilience/`, applied inside the
   provider base class. Both fail open if the cache is unavailable.

---

## 6. Subsystems

### `apps/prompt_library` — the demand side

Models what people actually ask, so audits probe realistic questions rather than
invented ones. `Industry`, `Prompt`, `PromptVariation`, `IntentBucket`,
`IndustryTrend`, `BrandPrompt`, `PromptFanout`, `BenchmarkPack`. Pluggable miners
(Reddit, SerpAPI / DataForSEO, LLM synthesis) degrade to no-ops when API keys are
absent. Services cover dedup (embedding cosine with a trigram fallback), paraphrase,
stratified sampling with seeded reproducibility, demand scoring, and effectiveness
scoring. Beat jobs mine daily and recompute scores nightly.

### `apps/citations` — source influence

`Citation`, `DomainClassification` (cache), `SourceInfluenceSnapshot` (per provider x
industry x website x period), `SourceScan` / `SourceScanResult`. Extractors are
pluggable: Perplexity native, Gemini grounding chunks, a regex fallback, and an
optional LLM-assisted supplement. `domain_classifier` labels each domain and detects
per-tenant `your_site` versus `competitor_site`. Runs as a post-save hook on
`LLMRankingResult`, gated by `CITATION_EXTRACTION_ENABLED`.

### `apps/rag` — the per-tenant knowledge base

`KnowledgeSource` (one ingested URL) to `KnowledgeChunk` (embedded segments).
Embeddings are OpenAI `text-embedding-3-small` (1536-dim) with a deterministic 256-dim
hash fallback for tests and key-less environments.

**Storage is a `JSONField`, not pgvector.** Cosine similarity is computed in Python
over a candidate set scoped to `(user, website)`, which keeps brute-force scoring
fast at the corpus sizes expected per tenant. The rationale is documented at
`apps/rag/models.py` and `apps/rag/ARCHITECTURE.md`; migrating to pgvector with an
HNSW index is a tracked follow-up in `apps/rag/.todo.md`, gated on any single tenant
exceeding 10k chunks. `retrieve()` is the only call site that touches embeddings, so
the swap stays local.

Each audit ingests its own enrichment context back into the knowledge base, so
subsequent audits draw from a richer seed.

### `apps/brand_vault` — ground truth and Brand Security

Two related surfaces in one app.

**Brand Vault** (`/api/v1/brand-vault/`) stores `BrandFact` subject-predicate-object
triples extracted from the knowledge base, with `source_chunk` provenance, confidence,
approval status, and temporal versioning (`version_from`, `version_to`,
`superseded_by`). `FactRevision` keeps a before/after audit trail. `ToneSample`
captures brand voice for the content studio.

**Brand Security** (`/api/v1/brand-security/`) is a scheduled monitoring framework.
`apps/brand_vault/services/security/registry.py` registers five agents:

| Agent | Watches for |
|---|---|
| `narrative_watch` | Emerging narratives before they trend |
| `llm_truth` | Wrong, outdated or harmful claims LLMs make about you |
| `serp_reputation` | Negative pages outranking you, bad queries you rank for |
| `sentiment_pulse` | Sentiment shifts and harmful mentions across social |
| `impersonation` | Typosquat domains and fake handles using your brand |

They draw on pluggable sources in `apps/brand_vault/services/security/sources/` (SERP,
Reddit, X, Google Trends, LLMs) and emit `SafetyAlert` rows. `judge.py` grounds
severity judgements in per-tenant RAG chunks rather than asking a model cold.
`BrandSecurityAgent` holds per-website enablement, sensitivity and schedule;
`orchestrator.py` runs them and advances `next_run_at`. Scans are queued
asynchronously and polled via `scan/status/`.

### `apps/content_studio`

Turns visibility gaps into content. `ContentBrief` records the gap type, impact score,
target format and target prompt, and links the `BrandFact` rows the draft must stay
consistent with. `ContentDraft` holds markdown, HTML, JSON-LD, a voice score and an
accuracy score, behind an approve/regenerate workflow. A daily beat job generates
briefs; gated by `CONTENT_STUDIO_BRIEF_GENERATION_ENABLED`.

### `apps/agents` — hireable agents

Agent *types* are defined in code (`apps/agents/catalog.py`): `visibility_analyst`,
`citation_hunter`, `content_strategist`, `lead_scout`, `brand_watchdog`. Each spec
carries a persona prompt, a gatherer callable and an allowlist of action types.
`HiredAgent` stores per-user, per-website state — schedule, config, and the Slack or
Discord connection for the digest. Runs produce `AgentInsight` rows, which propose
`AgentAction` rows. **Every action is human-approval-gated**; actions are limited to
`ingest_url`, `draft_brief` and `notify`. `AgentMessage` holds the chat transcript.
Scheduling mirrors `LLMRankingSchedule` so dispatcher logic stays consistent.

### `apps/search_console`

Google Search Console OAuth and sync. `GscDailyTotal`, `GscQueryStat`, `GscPageStat`
all extend an abstract metrics base. Real search queries feed back into the prompt
library. Daily sync with per-user API budgets and a retention window.

### `apps/analytics`

First-party web analytics from the JS pixel in `pixel/`. `Visitor` (fingerprint and IP
are hashed, not stored raw) to `Session` to `PageEvent`, plus funnels, tracked links
and an access log. Ingest is public, authenticated by `pixel_key`, and accepts
`text/plain` so `navigator.sendBeacon` works. Live views stream over Channels
(`ws/analytics/<website_id>/live/`).

### `apps/accounts`, `apps/billing`, `apps/websites`, `apps/notifications`, `apps/onboarding`

Custom `AUTH_USER_MODEL`, organizations and memberships, OTP email verification,
Google OAuth, and the `AITokenUsage` ledger. Stripe subscriptions with an idempotency
ledger (`BillingEvent`) keyed on the Stripe event id. Websites own settings,
memberships, webhook endpoints and integrations, with OAuth tokens and webhook secrets
stored through `core/encryption/field_encryption.py::EncryptedTextField`. Notification
delivery covers in-app, email, Slack, Discord and Telegram. Onboarding drives the
Login to Onboarding to Paywall to App flow; `GET /api/v1/auth/session/` returns the
`next_route` the client should send the user to.

`apps/leads` is a stub. Its models are `managed=False` and exist only to satisfy
historical lazy FK references from analytics migrations.

---

## 7. Background jobs

`config/celery.py` defines the queue topology and the beat schedule.

| Queue | Carries |
|---|---|
| `default` | analytics, pixel, accounts — fast in-process work |
| `ai` | `llm_ranking`, `citations`, `brand_vault`, `content_studio`, agent runs |
| `integrations` | Search Console, OAuth token refresh, agent action execution |
| `webhooks` | Outbound webhook delivery to user-controlled URLs |

The prod worker consumes `default,high,low,ai,integrations,webhooks`.

Scheduled work includes three 15-minute dispatchers (`dispatch_scheduled_audits`,
`dispatch_agent_runs`, `dispatch_scheduled_security_agents`), OAuth token refresh
every 15 minutes, hourly analytics aggregation, and a nightly block: GSC sync 03:00,
fact-embedding refresh 03:30, prompt mining 04:00, demand scores 05:00,
source-influence snapshots 05:30, domain classification 06:00, content briefs 06:15.
Monthly jobs hard-delete soft-deleted rows and check encryption-key rotation.

Note that `CELERY_TASK_TIME_LIMIT` is 300 seconds. Individual cell tasks fit
comfortably; long serial operations should be decomposed rather than run as one task.

---

## 8. Internal services (`services/`)

Commonly used capability logic runs as owned downstream services, each in its own
container with a unique internal FQDN:

| Service | Internal FQDN | Owns |
|---|---|---|
| `intelligence` | `http://intelligence.ftb.internal:8000` | LLM brand/sentiment/issue extraction, SERP relevance gate |
| `sources` | `http://sources.ftb.internal:8000` | Perplexity web search, Reddit/Yelp/page content readers (SSRF-guarded) |

Pattern:

- **Network:** compose default bridge only. The FQDNs are compose network aliases;
  there are no published ports, no nginx routes, and no public DNS. A browser can
  never reach these services — only `web` and `celery` can, over the Docker network.
- **Auth:** static per-service bearer token (`INTELLIGENCE_AUTH_TOKEN`,
  `SOURCES_AUTH_TOKEN`) from `.env.prod`, injected into both the service and its
  Django callers. A service with an empty token refuses requests (503) rather than
  failing open.
- **Stateless services, stateful facades:** quotas (`core.quota`), circuit breakers
  and `AITokenUsage` cost recording stay in the Django facade modules
  (`apps/citations/services/{source_sentiment,web_search,content_reader}.py`). The
  services return usage numbers; the facades record them.
- **In-process fallback (single source of truth):** the pure logic lives in
  `services/*/logic.py`, importable without FastAPI or Django. When
  `INTELLIGENCE_SERVICE_URL` / `SOURCES_SERVICE_URL` are unset (dev, tests, CI), the
  facades call that logic in-process with identical behavior. Production sets the URLs
  in `.env.prod` to switch to HTTP. Rollback is therefore instant: blank the URL vars
  and restart web/celery.
- **Fail-soft:** a down service degrades exactly like a missing API key — single scan
  rows get error markers, the relevance gate fails open, searches return empty. It
  never breaks request handling.
- **SSRF note:** `services/sources/{url_safety,safe_http}.py` are Django-free copies of
  `core/validators/*` (which other apps still import and which raise Django
  `ValidationError`). Keep them in sync; `services/sources/tests/test_sources_ssrf.py`
  mirrors the guard tests.

---

## 9. Deployment

Merging to `main` deploys to production. `.github/workflows/deploy.yml` waits for the
`Lint` check on the same commit, SSHes to the EC2 host, and runs
`bash scripts/deploy.sh deploy --clean`, which pulls, rebuilds the images on the host,
migrates, collects static files and smoke-tests `/health/`.

Consequences worth knowing:

- **Images are built on the host.** There is no registry for the backend; the EC2 box
  is the build farm. The one pulled image is the UI.
- **No blue/green.** The deploy takes the stack down before bringing it back up, so
  every release causes a brief outage.
- **No automated rollback.** Reverting means checking out an earlier SHA on the host
  and rebuilding; a forward migration that is not safely reversible needs a database
  restore first.
- **CI runs `ruff check .` and nothing else.** The test suite is not yet part of the
  gate that protects the auto-deploying branch. Run `pytest` locally before merging.

Full runbook, required secrets and the paywall entitlement switch: `DEPLOY.md`.
