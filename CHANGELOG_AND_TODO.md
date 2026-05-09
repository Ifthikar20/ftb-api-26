# GEO Platform Refactor — Changelog & TODO

Branch: `claude/understand-app-features-3Qen8` (PR #18)

## Done

### Cleanup — features removed
- `apps/competitors` deleted (whole Django app + frontend). Migration drops `competitors_*` tables.
- `apps/compliance` deleted. Migration drops `compliance_audit_log`. `audit_log()` now writes to text logs only; the Celery DB-write path is gone.
- `apps/leads` and `apps/social_leads` deleted. Migration drops all `leads_*` and `social_leads_*` tables. `WebsiteFactory` was relocated to `apps/websites/tests/factories.py`.
- Keyword tracking removed from `apps/analytics`: `TrackedKeyword`, `KeywordRankHistory`, `KeywordAlert`, `KeywordAlertEvent`, `KeywordScanConfig`, `PlatformContent` models gone; their views, URLs, services (`keyword_intelligence_service`, `seo_keyword_scanner`, `dataforseo_service`), and tasks (`execute_keyword_scan`, `fetch_platform_trends`, `run_auto_keyword_scans`, `check_keyword_alerts`) deleted.
- `HeatmapView` and the `/heatmap/` route deleted.
- Frontend pages removed: `LeadsPage`, `KeywordsPage`, `HeatmapPage`. Router routes, sidebar nav links, command-palette entries, store getters, and feature-gate flags all stripped.
- Cross-app references cleaned: `DashboardView` no longer queries `Lead`; notification reports trimmed to visitor/pageview metrics; seed commands cleaned; `core/tasks.hard_delete_soft_deleted` no longer touches `Lead`.

### Phase 1 — Prompt Library (demand-side prompts)
- New `apps/prompt_library` app: `Industry`, `Prompt`, `PromptVariation`, `PromptSampleRun`, `PromptSampleEntry`. 20 industries seeded.
- Pluggable miners: Reddit, SerpAPI / DataForSEO, LLM-synth (Claude/GPT meta-prompt). Graceful no-op when API keys are missing.
- Services: `dedup_service` (embedding cosine + trigram fallback), `paraphrase_service`, `sampler_service` (stratified / recent / top_demand with seeded reproducibility), `scoring_service` (demand score from source weight + recency + variation count).
- Celery beat: `mine-daily-prompts` (04:00), `compute-demand-scores` (05:00).
- DRF API at `/api/v1/prompt-library/`: industries, prompts (filterable), `preview-sample`, `use-library-sample`, `audit-sample`.
- Audit pipeline integration: `audit_runner.apply_to_audit(audit, prompt_source="vault" | "library" | "hybrid")`. New `prompt_source` field on `LLMRankingAudit` and `prompt_source_label` on `LLMRankingResult`.
- Frontend: `IndustryTypeahead`, `PromptSourceToggle`, `PromptPreviewDrawer`, `PromptLibraryPage`. Run Audit modal in `LLMRankingPage.vue` now shows the toggle + preview drawer; audit-result rows render provenance badges; new "Prompt Coverage" tile shows library / vault / custom percentages.
- Onboarding accepts `industry_id` (UUID) alongside legacy `industry` string.

### Phase 2 — Citations & Source Influence
- New `apps/citations` app: `Citation`, `DomainClassification` (cache), `SourceInfluenceSnapshot` (per provider × industry × website × period rollup).
- `domain_classifier` with rule-based + cache-backed lookup; per-tenant `your_site` and `competitor_site` detection.
- `url_normalizer` (tracking-param strip, apex-domain extraction).
- Pluggable extractors: Perplexity native, Gemini grounding chunks, regex fallback, optional LLM-assisted (low-confidence supplement for Claude/GPT).
- `extraction_service.extract_for_result` + Celery task hook into the audit pipeline (gated on `CITATION_EXTRACTION_ENABLED`).
- Daily Celery beat: `compute-source-influence` (05:30), `classify-unknown-domains` (06:00).
- DRF API at `/api/v1/citations/`: per-audit citations + source-influence, per-website rollups, global benchmark.
- Frontend: `SourceClassBadge`, `SourceBreakdownBar`, `CitationsDrawer`, `SourceInfluencePage` (period + provider filters, 4 stat tiles, per-provider breakdown cards, top domains table, rule-based recommendations).
- LLM Ranking audit detail integration: Citations stat tile, "View source influence" CTA, mini per-audit breakdown bar, per-row "N citations" pill that opens the drawer.
- Sidebar sub-nav: "Source Influence" link under LLM Ranking.

### UX
- One-time tour tooltips on `PromptLibraryPage` (3 steps) and `SourceInfluencePage` (5 steps). Reuses existing `OnboardingTooltip` component; localStorage-persisted dismissal under `fb_tour_prompt_library_v1` and `fb_tour_source_influence_v1`.

### Bug fixes
- `core/middleware/rate_limit.py` — `cache.incr()` was crashing with `ValueError: Key not found` under concurrent requests when the rate-limit window expired between `get` and `incr`. Now uses atomic `cache.add` + a try/except fallback. Was causing 500s on `/devices/`, `/chart/`, `/countries/` and a side-effect frontend logout.

### Migrations to run on deploy
```bash
python manage.py migrate accounts        # 0011 + 0012 drop tables
python manage.py migrate analytics       # 0009 + 0010 drop keyword/competitor tables
python manage.py migrate citations
python manage.py migrate prompt_library
python manage.py migrate llm_ranking
```

## Open TODOs

### Phase 1 follow-ups
- [ ] Plumb `website.industry_id` (UUID) onto `LLMRankingPage` so `PromptPreviewDrawer` actually loads sampled prompts. Currently it receives `null` because `auditForm.industry` is a string label, not an id, so the drawer skips its load.
- [ ] Industry filter on `PromptLibraryPage` selects the typeahead but doesn't pass `slug` to the list endpoint. Resolve `industry_id → slug` once and feed the API.
- [ ] Wire the audit POST handler to read `industry_id` from request and forward it to `apply_to_audit` (currently the view accepts the field but doesn't pass it through).
- [ ] Add tests for the Run-Audit modal flow (front + back) with `prompt_source="library"` and `"hybrid"`.

### Phase 2 follow-ups
- [ ] Backend `WebsiteSourceInfluenceView` returns raw snapshot rows; the page does the aggregation client-side. If you want a cleaner API, return a pre-aggregated `{ total_citations, breakdown, top_domains, by_provider }` shape from the view.
- [ ] `is_target` / `is_competitor` / `source_class` are not populated on the snapshot's `top_domains` payload. `SourceInfluencePage` enriches them client-side from `websiteCitations`. Move that enrichment server-side so the API is self-describing.
- [ ] Top-domains table sort is count-only; add column sorting (share, source_class, name).
- [ ] LLM-assisted extractor for Claude/GPT citations is stubbed but rate-limited; tune the trigger heuristic so it only runs on responses where regex extraction returns < N URLs and the response is non-trivial.
- [ ] No tests yet for the snapshot aggregation math under cross-tenant scenarios.
- [ ] Per-page citation snapshot to S3 (or filesystem cache) so we can later analyze "what about this page made the LLM cite it." Schema slot exists but storage isn't wired.

### Phase 3 — Brand Vault & Claim Verification (not started)
- [ ] `BrandFact` model on top of existing `apps/rag` knowledge base: subject, predicate, object, source_chunk_id, confidence, version_from, version_to.
- [ ] `Claim` and `ClaimMismatch` models keyed off `LLMRankingResult`.
- [ ] Claim extractor service — local Llama or Bedrock Claude with strict JSON schema. Eval harness with 50+ labeled examples before shipping.
- [ ] Verification engine — embed each claim, vector-search Brand Vault, cross-encoder rerank, score severity by factual divergence × audience reach × prompt frequency.
- [ ] Frontend: Accuracy dashboard (% verified, top mismatches, per-product-line breakdown), mismatch detail view (claim vs fact side-by-side), filters by product line / topic / severity / provider.
- [ ] Versioning UX — "this fact changed on date X" timeline.

### Phase 4 — Content Studio (not started)
- [ ] `apps/content_studio`: `ContentBrief`, `ContentDraft`, `PublishTarget`.
- [ ] Brief generation from gap signals (visibility, accuracy, citation).
- [ ] Bedrock Claude drafts grounded in Brand Vault facts.
- [ ] Brand-voice guard against Brand Vault tone samples.
- [ ] Output formats: blog, FAQ, Reddit-style answer, JSON-LD schema, landing page.
- [ ] Publish integrations: WordPress, Webflow, Shopify, HubSpot.
- [ ] Post-publish ROI loop: re-probe affected prompts, attribute score lift to drafts.

### Phase 5 — AWS migration (deferred until product-market fit)
- [ ] Trigger: 50+ paying customers OR 100k probes/day OR enterprise single-tenant requirement.
- [ ] Migration order: S3 dump → SQS broker → Aurora Serverless v2 → Step Functions for audit workflow → Bedrock for Claude → OpenSearch Serverless (vector) → EKS GPU pods.

### Cross-cutting / hygiene
- [ ] **Cost telemetry** — every LLM call tagged with `(business_id, audit_id, provider, model, tokens_in, tokens_out, cost_usd)` in an `LLMCallLog` table. Required before scaling probes.
- [ ] **Provider router abstraction** — single `apps/llm_ranking/services/providers/router.py` so probe calls have one place for cost tracking, retries, rate-limit handling, and model swaps.
- [ ] **Eval harness for LLM-mediated extraction** (mentions, citations, claims) — labeled examples, regression tests, monitored accuracy per release. 20–30% of phase-3 engineering should live here.
- [ ] **Multi-tenant data isolation review** — every endpoint, every query, especially Brand Vault. One leak ends the company.
- [ ] **Per-tenant rate-limit policy** — current middleware is per-IP; production should be per-user / per-org.
- [ ] **Provider deprecation plan** — Claude / GPT / Gemini / Perplexity all change. Plan 1–2 weeks/quarter for adapter maintenance.

### Known small bugs / loose ends
- [ ] `LLMRankingPage.vue` is large; PromptPreviewDrawer + CitationsDrawer were added without refactoring. Worth a small UX pass to consolidate.
- [ ] Dev-runner warned about migration drift on `citations` and `prompt_library`; captured as `0002_auto_phase2_drift` and `0003_auto_phase2_drift` (cherry-picked from `claude/llm-ranking-algorithms-ygB7i`, commit `f80eebe`). No data impact, just index renames.
- [ ] Four migration files showed `M` after the cherry-pick (`accounts/0010`, `analytics/0003`, `analytics/0008`, `analytics/0010`) — confirm the diffs are formatting-only and commit, or revert.
