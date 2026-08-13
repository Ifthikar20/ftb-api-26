# FetchBot API

Backend for [fetchbot.ai](https://fetchbot.ai) — a multi-tenant SaaS for **Generative
Engine Optimization (GEO)**. It measures and improves how a brand appears in answers
produced by large language models, the way traditional SEO tools measure Google
rankings.

The flagship feature is the **LLM Ranking Audit**: given a business profile, the system
asks Claude, GPT, Gemini, Perplexity and Grok the kinds of questions a buyer would ask,
parses the answers, and scores brand visibility, citation share, sentiment and
competitive rank over time. Around that sit a prompt library (what people actually
ask), citation analysis (which domains the models cite), a per-tenant knowledge base
that grounds the prompts, brand-security monitoring, and a content studio that turns
visibility gaps into drafts.

> **This repository is backend only.** The Vue 3 UI lives in the separate `ftb-ui`
> repo and ships to production as `ghcr.io/ifthikar20/ftb-ui`. The `frontend/`
> directory here is a leftover build cache and is not used.

## Stack

Python 3.12 · Django 5.1 · Django REST Framework · PostgreSQL 16 · Redis · Celery 5.4
· Channels (ASGI WebSockets) · drf-spectacular

Two internal **FastAPI** sidecars live under `services/` (`intelligence`, `sources`).
They are reachable only over the Docker network. When their URLs are unset, the Django
facades import the same logic from `services/*/logic.py` and run it in-process, so dev,
tests and CI behave identically without the containers.

## Quickstart

```bash
make install                                          # pip install -r requirements/dev.txt
cp .env.prod.example .env                             # then fill it in
docker compose -f docker/docker-compose.dev.yml up -d db redis
make migrate
make superuser
```

You need a local Postgres on `5432` for the test suite — `config/settings/test.py`
hard-codes `growthpilot_test` on localhost and does not read it from the environment.

In dev, `CELERY_TASK_ALWAYS_EAGER` is on, so Celery tasks run inline in the web process
and you do not need a worker to exercise audit flows.

## Commands

| Command | What it does |
|---|---|
| `make test` | `pytest --cov=apps --cov-report=term-missing -v` |
| `make lint` | `ruff check .` — the same gate CI runs |
| `make format` | `black .` then `isort .` |
| `make check-all` | ruff + mypy + pytest |
| `make migrate` / `make migrations` | Apply / create migrations |
| `make celery` / `make celery-beat` | Start a worker / beat locally |
| `make generate-key` | Print a Fernet key for `FIELD_ENCRYPTION_KEY` |
| `bash scripts/deploy.sh help` | Deploy, migrate, seed, health, eval, install-hooks |

CI (`.github/workflows/ci.yml`) runs `ruff check .` only — the test suite is not yet
wired into CI, so run `pytest` locally before merging.

## Apps

Each lives under `apps/` and mounts at `/api/v1/<name>/`.

| App | Responsibility |
|---|---|
| `llm_ranking` | LLM Ranking Audits: prompt generation, provider fan-out, mention extraction, scoring |
| `prompt_library` | Mines and scores the prompts real buyers ask; industries, variations, benchmark packs |
| `brand_vault` | `BrandFact` ground truth for claim verification, plus the Brand Security agents |
| `analytics` | First-party web analytics from the JS pixel in `pixel/`, with live WebSocket views |
| `citations` | Which sources LLMs cite about you; domain classification and source-influence rollups |
| `search_console` | Google Search Console OAuth and sync; feeds real queries into the prompt library |
| `rag` | Per-tenant knowledge base that grounds prompts and the truth judge |
| `billing` | Stripe subscriptions, plans, paywall, usage records |
| `accounts` | Custom `User`, organizations, OTP verification, Google OAuth, the AI cost ledger |
| `agents` | Hireable AI agents on a schedule; all actions are human-approval-gated |
| `content_studio` | Turns visibility gaps into content briefs and drafts |
| `websites` | The tenant root object. Nearly every other model hangs off a `Website` |
| `notifications` | In-app notifications plus Slack, Discord, Telegram and email delivery |
| `onboarding` | First-run scan-and-save flow |
| `leads` | Stub only (`managed=False`), kept to satisfy historical FK references |

`core/` holds the cross-cutting infrastructure every app depends on: middleware,
DRF interceptors (response envelope, pagination, throttling, exception handler),
permissions, field encryption, circuit breakers, SSRF validators, the `AITokenUsage`
cost ledger (`core/ai_tracking.py`) and per-user daily API budgets (`core/quota.py`).

## Two conventions worth knowing before you add an endpoint

**Tenant scoping is centralized.** Extend `TenantScopedAPIView` (or
`TenantScopedListAPIView`) from `core/views/base.py` and call `self.get_website()`.
It resolves the `website_id` URL kwarg through `WebsiteService.get_for_user()`, which
raises 404 — never 403 — so object IDs cannot be probed. Do not hand-roll the
ownership check.

**Cost tracking is enforced by construction.** LLM calls go through a provider class
in `apps/llm_ranking/providers/`. Subclasses implement only `_call()`; the base class
owns the circuit breaker, rate limiter, timing, error normalization and the write to
`AITokenUsage`. Adding a provider therefore cannot silently skip cost accounting.

## Documentation

| Document | Contents |
|---|---|
| `docs/ARCHITECTURE.md` | System design, the audit pipeline end to end, subsystem breakdown |
| `docs/INFRASTRUCTURE.md` | What runs in production, sync vs async paths, capacity, inspection recipes |
| `DEPLOY.md` | Release flow, required secrets, manual deploy, rollback, pre-deploy checklist |
| `apps/*/ARCHITECTURE.md` | Per-app design notes (11 apps have one) |
| `apps/*/.todo.md` | Per-app backlog |
| `TODO.md`, `CHANGELOG_AND_TODO.md` | Historical project backlog and refactor log |
| `CLAUDE.md` | Rules for AI agents working in this repo |

Architecture diagrams: `docs/architecture.drawio`, `docs/business-flow.drawio`.
