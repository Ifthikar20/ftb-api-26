# Compliance App

## Purpose

Provides an immutable, queryable audit trail for SOC 2, GDPR, and regulatory compliance. This is a cross-cutting concern that captures WHO did WHAT, WHEN, WHERE, and the OUTCOME across the entire platform.

## Architecture

```
Any API Request / System Event
  │
  ├── Middleware (AuditMiddleware)
  │     └── Captures request context (user, IP, path, method)
  │
  ├── core.logging.audit_logger.audit_log()
  │     ├── Writes to structured log files (text-based)
  │     └── Enqueues Celery task for DB write
  │
  └── Celery Worker
        └── AuditLog.objects.create(...)  → Immutable DB record
```

## Models

| Model | Purpose |
|---|---|
| `AuditLog` | Immutable audit record. Captures user ID/email, IP, user agent, event name (dot-notation), action type (create/read/update/delete/login/logout/export/api_call/webhook/system), resource type/ID, HTTP method/path, status code, duration, metadata JSON, success flag, and error message. |

## Design Principles

1. **Write-only** — Records can be created but NEVER updated or deleted via ORM. The `save()` method raises `ValueError` if the record already exists.
2. **Append-only permissions** — Django `default_permissions = ("add", "view")` prevents delete from Django admin.
3. **Async writes** — Audit log writes are queued via Celery to avoid performance impact on API responses.
4. **Dual storage** — Records are written to both database (queryable) AND structured log files (archivable).
5. **No PII in metadata** — The `metadata` JSON field explicitly must never contain passwords, PII, or sensitive data.
6. **24-month retention** — Automated cleanup task purges records older than 24 months.

## Celery Tasks

| Task | Schedule | Purpose |
|---|---|---|
| `write_audit_log` | On-demand (async) | Persist audit record to database |
| `cleanup_old_audit_logs` | Monthly | Remove records older than 24 months |

## Index Strategy

Five indexes optimized for common compliance queries:
- `(user_id, -timestamp)` — "What did user X do?"
- `(event, -timestamp)` — "When did event Y happen?"
- `(action, -timestamp)` — "All delete actions this month"
- `(resource_type, resource_id)` — "Full history of resource Z"
- `(-timestamp, success)` — "Recent failures"

## Key Design Decisions

- **Separate app** — Compliance is isolated from business logic, with no reverse dependencies.
- **Dot-notation events** — Events use hierarchical names like `user.login`, `billing.checkout_created`, `lead.scored` for easy filtering and grouping.
- **Immutability enforced in code** — Not just a convention; the `save()` override physically prevents updates.

## Dependencies

- **Depends on:** None (standalone)
- **Depended on by:** `billing` (webhook audit logging), `core` (audit_log utility)
