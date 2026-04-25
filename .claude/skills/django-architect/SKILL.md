---
name: django-architect
description: Django and DRF architecture expertise for the FTB API codebase. Use when the user asks to design or refactor models, plan migrations, structure new apps, optimize ORM queries, design DRF resources, choose between Celery/async, or evolve the multi-tenant architecture.
---

# Django Architect - FTB API

## Project context

FTB API is a multi-tenant Django + DRF backend serving a Vue 3 SPA.

- **Layout**: `config/` (settings split, urls, asgi/wsgi, `celery.py`),
  `apps/` (~16 domain apps), `core/` (shared), `conftest.py` for pytest.
- **Domain apps**: `accounts`, `agents`, `analytics`, `billing`,
  `competitors`, `compliance`, `leads`, `llm_ranking`,
  `notifications`, `social_leads`, `websites`.
- **Async**: Celery via `config/celery.py`.
- **Frontend**: `frontend/` (Vite + Vue 3 + Pinia + axios) - shapes the API contract.

## Architectural principles for this repo

1. **One app per bounded context**. Resist cross-app foreign keys outside of
   `accounts` (tenant/user) and `core`. If `apps/leads` needs `apps/competitors`
   data, prefer a service function or signal, not a hard FK.

2. **Tenant model is load-bearing**. Every domain model should carry
   `tenant = ForeignKey("accounts.Tenant", on_delete=CASCADE, db_index=True)`
   and every default manager should scope by tenant. Recommend a
   `TenantManager` + `TenantScopedModel` base in `core/`.

3. **Models**
   - Explicit `related_name`, `db_index` on FKs used in filters,
     `UniqueConstraint(fields=[...], name=...)` over `unique_together`.
   - `CheckConstraint` for invariants (e.g., billing amounts >= 0).
   - Avoid `null=True` on `CharField`; use `default=""`.
   - Soft-delete only when truly needed; otherwise hard delete + audit log.

4. **Migrations**
   - Backwards-compatible deploys: add nullable -> backfill data migration ->
     enforce NOT NULL in a later migration.
   - Never edit historical migrations; squash only with care.
   - Heavy backfills go to Celery, not migration `RunPython`.

5. **DRF design**
   - `ViewSet` + `Router` for CRUD; `APIView` for bespoke actions.
   - Serializers: explicit `fields = [...]`, `read_only_fields` for tenant/user.
   - One serializer per representation (list/detail/write) when they diverge.
   - Pagination, filtering (`django-filter`), throttling configured globally.
   - Versioning: URL-path versioning is simplest given the SPA.

6. **ORM performance**
   - `select_related` for FKs in detail; `prefetch_related` with `Prefetch(...)`
     for nested lists. The `analytics`, `leads`, and `competitors` apps are
     the most likely N+1 hotspots.
   - Use `only`/`defer` for wide tables; `annotate`/`aggregate` over Python loops.
   - Add `nplusone` to test settings to fail loud on regressions.

7. **Celery boundaries**
   - Tasks are idempotent and accept primitive args (IDs, not model instances).
   - Long-running work in `apps/websites`, `apps/llm_ranking`,
     `apps/competitors` belongs in tasks with retry/backoff and per-tenant rate limits.
   - Use `bind=True` and `autoretry_for=(...)` with capped `retry_backoff`.

8. **LLM and external services**
   - Wrap third-party clients in a service module per app
     (`apps/llm_ranking/services/openai.py`, etc.).
   - Inject via simple functions, not heavy DI; mock at the service boundary in tests.

9. **Settings** (`config/settings/`)
   - `base.py` + `dev.py` / `prod.py` / `test.py`. 12-factor env vars.
   - No imports of settings at module top inside apps; use `django.conf.settings` lazily.

10. **Testing** (`conftest.py`, `apps/*/tests/`)
    - `pytest-django`, factory_boy, `--reuse-db` locally.
    - Tenant isolation tests are mandatory for every new endpoint.

## Output style

Recommend the simplest design that meets the requirement. Show trade-offs
explicitly. Reference code with `apps/<app>/<file>:<line>`. When suggesting
a refactor that touches multiple apps, list the migration steps in deploy order.
