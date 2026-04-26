# FTB API — Project TODO

Tracks everything that must happen to ship the Login → Onboarding → Paywall → App
flow and the LLM Ranking first-run experience, plus infrastructure cleanup
surfaced during development.

Status key:
- [ ] Not started
- [~] In progress / partial
- [x] Done (kept for context; safe to delete once merged)

---

## P0 — Blockers. Cannot ship the paywall flow without these.

### Stripe setup
- [ ] Create Stripe product + monthly price for Starter at $29 USD. Copy the price id.
- [ ] Create Stripe annual price for Starter (~$290 USD for 17% savings). Copy the price id.
- [ ] Create Stripe product + monthly price for Pro at $96 USD. Copy the price id.
- [ ] Create Stripe annual price for Pro (~$960 USD). Copy the price id.
- [ ] Archive or reprice the legacy $39 Starter price in Stripe so it is not selectable.
- [ ] Add env vars in local, staging, and prod:
  - `STRIPE_STARTER_PRICE_ID`
  - `STRIPE_STARTER_ANNUAL_PRICE_ID`
  - `STRIPE_PRO_PRICE_ID`
  - `STRIPE_PRO_ANNUAL_PRICE_ID`
- [ ] Confirm `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are set in all envs.
- [ ] Point a Stripe webhook at `/api/v1/billing/webhook/` in each environment and subscribe to `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.

### Product decisions that unblock paywall content
- [ ] Finalize feature bullets per tier (Starter, Pro, Business). Update `frontend/src/constants/pricing.js` and keep `core/utils/constants.py::PLAN_LIMITS` in sync.
- [ ] Decide the Business-tier contact target. If email, confirm address in `pricing.js`. If Calendly, replace the `mailto:` link with the Calendly URL.
- [ ] Decide trial behavior. Current code treats `TRIALING` as paying only when `stripe_subscription_id` is set. Confirm that is desired, or switch to “any TRIALING counts.”
- [ ] Decide what happens when a paying user’s subscription lapses (webhook → status `past_due` or `canceled`). Should they be re-directed to `/paywall` on next navigation? (Currently yes — `next_route` in `SessionView` returns `paywall` whenever `is_paying` is false.)
- [ ] Decide whether `/paywall` should allow “downgrade to free trial of X audits” or stay a hard gate. Today it is a hard gate.

### Session / gate correctness
- [ ] Backfill: any existing users without a `Subscription` row will get `next_route == "paywall"` on first login. Confirm this is desired, or write a one-time script that grandfathers existing users onto a chosen plan.
- [ ] Decide how admins and internal users bypass the paywall (e.g. staff flag short-circuit in `SessionView`).

---

## P1 — Ship-blocking once P0 is resolved.

### Migrations and local dev
- [ ] Apply the pending migration: `python manage.py migrate` (the untracked `apps/llm_ranking/migrations/0005_merge_20260424_1557.py`).
- [ ] Run `python manage.py makemigrations` after the `Plan.PRO` enum addition and verify no new migration is produced. If Django emits one, commit it.
- [ ] Restart runserver so the new `CONN_MAX_AGE = 0` in `config/settings/dev.py` takes effect.
- [ ] Local Postgres: raise `max_connections` to 300. `psql -U postgres -c "ALTER SYSTEM SET max_connections = 300;"` then restart Postgres.
- [ ] Run Celery worker locally so queued audits actually execute: `make celery`. Without this, every POST to `/audits/` sits in `pending` forever.
- [ ] Run Celery beat locally so scheduled audits fire: `make celery-beat`.
- [ ] Ensure `.env` has `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` / `GEMINI_API_KEY`, `PERPLEXITY_API_KEY` — otherwise LLM audits will fail per provider.
- [ ] Optional: apply the docker-compose.dev.yml upgrade (already committed). If you want pre-existing host DB data in Docker, export/import manually — the new named volume starts empty.

### Tests
- [ ] Run the full Django suite: `pytest apps/llm_ranking/ apps/accounts/ apps/billing/`. The LLM ranking tests were updated; confirm they pass.
- [ ] Write tests for `SessionView` (`apps/accounts/tests/test_views.py`):
  - No website → next_route == "onboarding".
  - Website with `onboarding_completed=False` → "onboarding" + correct `first_incomplete_website_id`.
  - Websites done, no subscription → "paywall".
  - Websites done, `Subscription(status=ACTIVE)` → "app".
  - Websites done, `Subscription(status=TRIALING, stripe_subscription_id=None)` → "paywall".
  - Websites done, `Subscription(status=TRIALING, stripe_subscription_id="sub_...")` → "app".
- [ ] Write tests for `LLMRankingPreviewPromptsView`:
  - Returns prompts using `Website.name` / `industry` / `description` / `topics` by default.
  - Query-param overrides (`industry`, `location`, `keywords`) take precedence.
  - Tenant isolation: cannot preview prompts for another user’s website.
- [ ] Write a test for the new audit-create fallback path (already added: `test_create_audit_falls_back_to_website_fields`) — verify it passes.
- [ ] Frontend: add Vitest + Vue Test Utils setup if none exists. Cover:
  - `FirstRunLLMRanking.vue` form validation, prompt add/remove, `audit-started` emit.
  - `LLMRankingPage.vue` state machine: renders FirstRun when `audits.length == 0`, renders dashboard otherwise.
  - `PaywallPage.vue`: clicking a tier calls `billingApi.checkout` with correct plan code; Business tier calls `window.location` with contact target.
  - Router guard: `next_route == "paywall"` redirects any app route to `/paywall`.

### Paywall polish
- [ ] Add a visual tier indicator to the app (sidebar or topbar) showing current plan.
- [ ] Add a “Manage billing” link in user menu that hits `billingApi.portal()` (already implemented backend-side).
- [ ] Add a grace-period banner when `status == past_due` so users know why they’re being sent to paywall.
- [ ] Mobile-responsive check for `PaywallPage.vue` and `FirstRunLLMRanking.vue`.
- [ ] Replace placeholder styling tokens with your design system’s tokens where needed.

---

## P2 — Post-launch polish that was discussed but deferred.

### LLM Ranking UX
- [ ] Prompt intent selector (Recommendation / Comparison / Alternatives / Local / Persona / Review) in FirstRun so users can skew the generated prompts without typing.
- [ ] Show prompt-pack identity (“Using SaaS pack”) on FirstRun.
- [ ] Dev-mode mock LLM provider in `apps/llm_ranking/services/ranking_service.py` so running audits locally does not require real API keys or burn spend.
- [ ] Client-side minimum-length validation on business name / industry / custom prompts (today form accepts `"f"`).
- [ ] Per-audit status badge in the audit list (failed vs completed should be visually different).
- [ ] Countdown on the schedule banner (“Next run in 2d 3h”).
- [ ] Cost/latency estimate shown live as the user toggles providers — partially done, confirm numbers reflect reality.

### LLM Ranking backend
- [ ] Soft-cap audit runs per plan (Starter = 1 audit/month? Pro = daily?). Enforce in `LLMRankingAuditListView.post`.
- [ ] Rate-limit POST `/audits/` per user to prevent runaway LLM spend.
- [ ] Store per-provider actual cost and latency on `LLMRankingResult` for real cost/latency hints.
- [ ] Add an audit-level `error_message` field so failed runs have a user-visible reason.

### Onboarding
- [ ] Skip onboarding step if the user arrives via an invite flow (team member added to existing website).
- [ ] Detect existing Google account and pre-populate `Website.description` and `topics` via the existing `onboardingAssist` endpoint at the new `/app-onboarding` step instead of making the user fill them on the next page.
- [ ] Handle the case where a user deletes their only website — they should be bounced back to `/app-onboarding`, not left on a stale dashboard.

### Security
- [ ] Audit all new endpoints for tenant isolation: `SessionView` (user-scoped only), `LLMRankingPreviewPromptsView` (uses `TenantScopedAPIView.get_website` — confirm).
- [ ] Rate-limit `/api/v1/auth/session/` — currently no throttle.
- [ ] Do not commit `.env` or any file with Stripe secret keys.

---

## P3 — Tech debt surfaced during this change.

### Database
- [ ] Postgres connection exhaustion: `CONN_MAX_AGE=0` is a dev-only patch. For prod, set up pgbouncer or confirm gunicorn worker + Postgres `max_connections` arithmetic. Do NOT ship `CONN_MAX_AGE=0` globally.
- [ ] Audit for connection leaks: the original incident saw 99 idle conns on a 100-cap Postgres. Check management commands and Celery tasks for connections that are not closed.
- [ ] Confirm `debug_toolbar` is not enabled in staging/prod settings (`config/settings/staging.py`, `config/settings/prod.py`).

### Settings hygiene
- [ ] Remove `version: "3.9"` from `docker/docker-compose.dev.yml` — Compose flags it as obsolete.
- [ ] Document in `README.md` or `docs/` the required env vars for LLM providers and Stripe.

### Frontend
- [ ] `frontend/src/stores/app.js` still has `userPlan = ref('starter')` hardcoded — wire it to `authStore.session.subscription.plan`.
- [ ] `projectLimit = ref(-1)` (unlimited) — wire to `PLAN_LIMITS[plan].projects` from backend.
- [ ] Hide the “LLM Ranking” tab for Starter users (not in `PLAN_LIMITS[Plan.STARTER].tabs`).

### Observability
- [ ] Add Sentry (or your chosen error tracker) context for `SessionView` and `LLMRankingPreviewPromptsView`.
- [ ] Dashboard/metric: conversion rate at each step of Login → Onboarding → Paywall → App.
- [ ] Log `next_route` transitions so we can debug users stuck in onboarding or paywall loops.

---

## Reference — files touched in this change

Backend:
- `apps/accounts/api/v1/views.py` — `SessionView` added.
- `apps/accounts/api/v1/urls.py` — `/auth/session/` route.
- `apps/llm_ranking/api/v1/views.py` — `LLMRankingPreviewPromptsView` added; audit POST falls back to `Website` fields.
- `apps/llm_ranking/api/v1/urls.py` — `/preview-prompts/` route.
- `apps/llm_ranking/api/v1/serializers.py` — `business_name` / `industry` made optional.
- `apps/billing/api/v1/views.py` — `CheckoutView` accepts `pro`.
- `apps/billing/services/stripe_service.py` — `pro` plan wiring + limits.
- `core/utils/constants.py` — `Plan.PRO`, updated `PLAN_LIMITS`.
- `config/settings/dev.py` — `CONN_MAX_AGE = 0` for dev.
- `docker/docker-compose.dev.yml` — migrate-on-boot, celery-beat, raised max_connections, named volume.
- `apps/llm_ranking/tests/test_views.py` — updated and extended.

Frontend:
- `frontend/src/stores/auth.js` — `session` + `fetchSession()`.
- `frontend/src/router/index.js` — `/paywall`, `/app-onboarding`, gate guard.
- `frontend/src/pages/auth/LoginPage.vue` — `next_route` redirect.
- `frontend/src/pages/PaywallPage.vue` — new.
- `frontend/src/pages/AppOnboardingPage.vue` — new.
- `frontend/src/components/llm_ranking/FirstRunLLMRanking.vue` — new.
- `frontend/src/pages/LLMRankingPage.vue` — FirstRun gate.
- `frontend/src/api/llm_ranking.js` — `previewPrompts()`.
- `frontend/src/constants/pricing.js` — new.
