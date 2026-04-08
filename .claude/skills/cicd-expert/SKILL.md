---
name: cicd-expert
description: CI/CD and deployment expert for FTB API. Use before every commit and PR to scan staged changes for build, test, deployment, migration, settings, Docker, and dependency issues, and flag concrete fixes. Also use when designing or reviewing CI pipelines, release flows, or rollout strategy.
---

# CI/CD Expert - FTB API

## Project context

- **Backend**: Django + DRF, ~16 apps under `apps/`, Celery via `config/celery.py`, settings split in `config/settings/`.
- **Frontend**: Vue 3 + Vite SPA in `frontend/`.
- **Infra surface in repo**: `docker/`, `Makefile`, `requirements/`, `pyproject.toml`, `setup.cfg`, `scripts/`, `ssl/`, `fynda-deploy.pem` (rotate if real).
- Multi-tenant production system - migrations and settings changes are high-risk.

## Pre-commit / pre-push review checklist

Run this against the staged diff (`git diff --cached`) and the changed file list. Report findings as `file:line - severity - issue - fix`.

### 1. Migrations (`apps/*/migrations/`)
- New migration without a corresponding model change, or vice versa.
- `AddField` on a non-nullable column with no `default` and no data migration. Blocks deploy.
- `RemoveField` / `RenameField` / `AlterField` that is not backwards compatible with the currently running code (must be a multi-step deploy: add -> backfill -> switch -> drop).
- Heavy `RunPython` in a migration (should be a Celery task).
- Migration touches a large table without `atomic = False` + batched updates.
- Two migrations with the same number on the same branch (merge conflict waiting to happen).

### 2. Settings and secrets (`config/settings/`, `docker/`, `.env*`)
- `DEBUG = True` in anything but `dev.py`.
- Hardcoded `SECRET_KEY`, API keys, DB URLs, tokens, private keys.
- New `INSTALLED_APPS` entry without matching migration / urls wiring.
- `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` widened (especially `*`).
- New env var referenced in code but not documented in `docker/` / deploy config.
- `fynda-deploy.pem` or any `*.pem`, `*.key`, `*.env` staged.

### 3. Dependencies (`requirements/*.txt`, `pyproject.toml`, `frontend/package.json`, `package-lock.json`)
- Unpinned versions or `>=` ranges in production requirements.
- Lockfile not updated alongside `package.json`.
- New dependency with no rationale; check for known CVEs (`pip-audit`, `npm audit`).
- Removed dependency still imported somewhere.

### 4. Celery (`config/celery.py`, `apps/*/tasks.py`)
- New task without `bind=True`, retry policy, or idempotency.
- Task signature changed without a backwards-compatible shim - in-flight messages will crash workers on deploy.
- New beat schedule without timezone or jitter.

### 5. DRF / URLs (`apps/*/urls.py`, `apps/*/views.py`, `config/urls.py`)
- New endpoint without `permission_classes` (defaults may be too permissive).
- Removed or renamed endpoint still referenced by `frontend/src/api/`.
- Serializer with `fields = "__all__"`.

### 6. Frontend (`frontend/`)
- `frontend/package.json` changed but `frontend/dist` committed stale - `dist` should not be in commits at all; flag if staged.
- New env var (`VITE_*`) used in code but missing from build config / deploy.
- Hardcoded API base URL.
- Imports of files that do not exist (typo or rename).

### 7. Docker / deploy (`docker/`, `Makefile`, `scripts/`)
- Dockerfile change without a corresponding `requirements` rebuild step.
- New service in compose without healthcheck or resource limits.
- `latest` tag pinned in production images.
- Shell scripts without `set -euo pipefail`.

### 8. Tests
- New view / serializer / task without an accompanying test in `apps/<app>/tests/`.
- Test marked `skip` / `xfail` without an issue link.
- `conftest.py` fixture changes that can break other apps' tests.

### 9. Cross-cutting
- TODO / FIXME / `print(` / `console.log(` / `breakpoint()` / `debugger` left in.
- Large binary files staged.
- Commit message style mismatch with recent history (`git log --oneline -20`).

## Deployment readiness review (before merging to main)

1. Migration plan: list migrations in order, mark each as safe / requires-downtime / multi-step.
2. Env var diff: new vars added, removed, renamed - ensure deploy config is updated.
3. Backwards compatibility: can the new code run against the old DB schema for the rollout window? Can the old code run against the new schema during rollback?
4. Celery: are workers safe to restart mid-rollout? Any task signature changes need a two-phase deploy.
5. Static / build: `frontend` build step verified, asset hashing intact.
6. Rollback plan: documented and tested.

## Output format

```
[severity] file:line - issue
  fix: <one line>
```

End with a short summary: `N critical, M high, K medium`. If zero issues, say so explicitly.

## Note on automation

This skill reviews on demand. To run it automatically before every commit, a git hook or a Claude Code hook in `settings.json` is required - ask the user if they want that wired up.
