---
name: qa-ui-expert
description: QA expertise for the FTB Vue 3 frontend and its integration with the Django API. Use when the user asks to write or review UI tests, set up Playwright/Vitest, define acceptance criteria, audit accessibility, triage flaky tests, or test specific pages and components in frontend/.
---

# QA UI Expert - FTB Frontend

## Project context

The frontend is a Vue 3 SPA in `frontend/` talking to the FTB Django API.

- **Stack**: Vite, Vue 3 (`<script setup>`), Pinia stores, Vue Router,
  Tailwind v4, Chart.js + vue-chartjs, Vue Flow (node graph), axios.
- **Layout**: `frontend/src/{api, components, composables, layouts, pages,
  router, stores}`.
- **Backend it talks to**: multi-tenant DRF API. Domains include leads,
  competitors, audits, billing, voice agent, LLM ranking, analytics dashboards,
  notifications, gamification.

The app is data-heavy (charts, tables, pipelines) and tenant-scoped, so test
strategy must cover: auth + tenant context, table/chart rendering with real-ish
data, long-running async flows (audits, voice agent), and form validation tied
to DRF serializer errors.

## Test strategy for this codebase

1. **Pyramid**
   - **Unit (Vitest)**: Pinia stores, composables in `frontend/src/composables`,
     pure helpers. Fast, no browser.
   - **Component (Vitest + @vue/test-utils or Playwright CT)**: individual
     components in `frontend/src/components` with mocked stores.
   - **E2E (Playwright)**: critical user journeys against a seeded backend.

2. **Critical journeys to cover first**
   - Login + tenant context loads (`apps/accounts`).
   - Lead pipeline view: list, filter, detail, status change.
   - Competitor tracking + history chart card.
   - Audit run: kick off, poll status, view report.
   - Billing: view plan, upgrade flow, webhook-driven state change visible in UI.
   - Voice agent: start session, transcript renders, end session.
   - LLM ranking dashboard renders without N+1 errors from API.

3. **Selectors**
   - `getByRole`, `getByLabel`, `getByText` first.
   - Add `data-testid` only where semantics are insufficient (Vue Flow nodes,
     chart canvases). Never CSS class chains - Tailwind classes will churn.

4. **Stability rules**
   - No `page.waitForTimeout`. Wait on network (`page.waitForResponse`) or
     DOM conditions.
   - Seed data via API calls in `beforeEach`, not by clicking through the UI.
   - Each test creates and tears down its own tenant where feasible, to avoid
     cross-test bleed.
   - Mock `Date.now` and timers for charts and gamification streaks.

5. **Charts and Vue Flow**
   - Chart.js renders to `<canvas>`. Assert via the underlying data passed to
     the component (mount with props), not pixel snapshots, except for one
     visual-regression smoke test per chart.
   - Vue Flow: assert nodes/edges via the store, not DOM positions.

6. **Accessibility**
   - `@axe-core/playwright` on every page-level E2E.
   - Keyboard-only walkthrough for: login, lead detail, audit run, billing upgrade.
   - Color contrast checks against the Tailwind v4 token set.
   - Focus management on modal open/close and route changes.

7. **API contract**
   - Generate fixtures from real DRF responses; refresh when serializers change.
   - Add a contract test that hits a running test backend and validates the
     shape the frontend expects.

8. **Flake triage**
   - Capture trace + video + console + network on failure.
   - Quarantine, root-cause, then re-enable. Never `test.retry` to mask.

9. **CI**
   - Shard Playwright; run on PR; publish HTML report and traces as artifacts.
   - Fail the build on new axe violations.

## Deliverables

For any task: a short test plan, the spec files (`frontend/tests/...`),
selector recommendations, axe findings with severity, and a flake report
when relevant. Reference code with `frontend/src/<path>:<line>`.
