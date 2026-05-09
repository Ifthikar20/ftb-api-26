# Content Studio (Phase 4 backend)

Per-tenant content authoring loop. Takes ranked content gaps from the
recommendation pipeline, drafts grounded artefacts via Claude, runs voice
and accuracy guards, publishes to a configured destination, and measures
the resulting score lift.

## Flow

1. After each LLM ranking audit, `apps.llm_ranking.services.ranking_service`
   dispatches `apps.content_studio.tasks.generate_briefs_for_website`.
2. `services.brief_generator` mines three gap families:
   - Visibility — prompts where the brand is mentioned in fewer than 20%
     of provider results.
   - Accuracy — open `ClaimMismatch` rows with severity in
     (critical, high).
   - Citation — source classes where competitor share dwarfs the brand
     by more than 3x.
   Each gap is hashed into a `dedupe_key`; existing open or drafted
   briefs for the same gap are skipped to keep generation idempotent.
3. `services.drafter` builds a system prompt from the website's top
   `ToneSample`s and a user prompt with the brief, target keywords, and
   grounded `BrandFact`s. Calls the Anthropic SDK when a key is
   configured; falls back to a deterministic stub draft so the test suite
   runs offline.
4. `services.voice_guard` averages cosine similarity of draft chunks
   against tone-sample embeddings. `services.accuracy_guard` extracts
   sentence-level claims and verifies each against approved facts.
5. `services.publish_adapters` exposes adapters for WordPress, Webflow,
   Shopify, HubSpot, and a manual-export adapter. Real HTTP calls are
   gated by `CONTENT_STUDIO_PUBLISH_LIVE`; the default behaviour is a
   dry-run that returns the payload that would have been sent.
6. After successful publish, `services.roi_tracker.schedule_roi_measurement`
   queues a delayed `measure_roi` task that compares pre/post visibility
   and citation counts for the affected prompts and persists an
   `ROIAttribution` row.

## Models

- `ContentBrief` — a ranked gap with target format, headline, structure,
  keywords, and a many-to-many of grounded facts.
- `ContentDraft` — drafted artefact with markdown body, optional JSON-LD,
  voice and accuracy scores, and a revision counter.
- `PublishTarget` — provider config per tenant.
- `PublishLog` — append-only record of publish attempts.
- `ROIAttribution` — measured score lift for a published draft.

## API

All endpoints live under `/api/v1/content-studio/` and are tenant-scoped
to the requesting user's websites via `core.views.TenantScopedAPIView`.

## Settings

- `CONTENT_STUDIO_BRIEF_GENERATION_ENABLED` — when True, the audit
  finalize hook dispatches brief generation (default True).
- `CONTENT_STUDIO_PUBLISH_LIVE` — when True, publish adapters issue real
  HTTP requests. Defaults to False so dev environments stay offline.

## Deferred

- Real auth flows for OAuth-style providers (Webflow / HubSpot scopes).
- Encrypted-at-rest storage of `PublishTarget.config` secrets.
- Scheduled re-probe of prompts via the ranking pipeline (currently the
  ROI tracker re-reads existing results rather than triggering a fresh
  audit).
