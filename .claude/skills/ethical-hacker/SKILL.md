---
name: ethical-hacker
description: Authorized offensive security review of the FTB API Django backend and Vue frontend. Use when the user asks to find vulnerabilities, run a pentest-style audit, check OWASP Top 10, review auth/billing/lead-handling endpoints, or simulate attacker reasoning. Defensive and educational use only.
---

# Ethical Hacker - FTB API

## Project context

FTB API is a multi-tenant marketing/lead-intelligence platform.

- **Backend**: Django + DRF in `config/` with domain apps in `apps/`:
  `accounts` (auth, tenants, users), `billing` (payments, subscriptions),
  `leads` + `social_leads` (PII-heavy lead data), `competitors`, `audits`,
  `llm_ranking`, `voice_agent` (telephony/LLM), `notifications`, `websites`,
  `compliance`, `analytics`, `gamification`, `strategy`, `agents`.
- **Async**: Celery (`config/celery.py`).
- **Frontend**: Vue 3 SPA in `frontend/` calling the API via `axios`.

High-value targets in this codebase:
1. `apps/accounts` - authentication, password reset, session/JWT, tenant isolation.
2. `apps/billing` - payment webhooks, price tampering, signature verification, idempotency.
3. `apps/leads` and `apps/social_leads` - IDOR across tenants, PII exposure, mass-assignment in serializers.
4. `apps/voice_agent` - prompt injection from caller transcripts, SSRF via tool calls, webhook auth.
5. `apps/llm_ranking` - prompt injection, untrusted output rendered to users.
6. `apps/websites` and `apps/audits` - SSRF when crawling/auditing external URLs (must block RFC1918, link-local, metadata IPs).
7. `config/settings` - `DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY` handling, CORS, CSRF trusted origins.

## Review playbook

For any in-scope target:

1. **Map the attack surface**: list URL routes, DRF viewsets, permission classes, serializer fields, raw SQL, and Celery task entry points.
2. **Tenant isolation**: confirm every queryset is filtered by `request.user`'s tenant/account. Flag any `.objects.all()` reachable from a view. IDOR is the most likely critical bug here.
3. **AuthZ matrix**: for each endpoint list (anon, authed-other-tenant, authed-same-tenant-wrong-role, owner). Missing `permission_classes` defaults are a red flag.
4. **Serializers**: never `fields = "__all__"` on models with sensitive fields (`is_staff`, `tenant_id`, `password`, billing tokens). Check `read_only_fields`.
5. **Billing**: verify webhook signature checks, replay protection, idempotency keys, and that price/amount come from server-side product records, not client input.
6. **Voice/LLM apps**: treat all transcripts and model outputs as untrusted. Check tool-call allowlists and outbound HTTP egress.
7. **External fetchers** (`audits`, `websites`, `competitors`): SSRF guard - resolve hostname, reject private ranges, disable redirects to private IPs, set timeouts.
8. **Celery tasks**: arguments are trust-boundary inputs if enqueued from user actions; validate before re-querying.
9. **Frontend**: check `frontend/src/api` for token storage (avoid `localStorage` for long-lived auth), and any `v-html` usage for XSS.

## Reporting format

For each finding:
- **Location**: `apps/<app>/<file>:<line>`
- **Severity**: Critical / High / Medium / Low
- **Scenario**: concrete attacker steps against this code
- **Fix**: minimal diff
- **Test**: a `pytest` that fails today and passes after the fix

## Hard limits

- In-scope: this repository only. No live attacks against deployed infra unless the user explicitly authorizes and provides scope.
- No exploit code beyond what is needed to demonstrate the issue in a test.
- No detection-evasion guidance. Stop and ask if scope is unclear.
