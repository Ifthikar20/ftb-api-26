# Billing App

## Purpose

Manages subscriptions, invoices, usage metering, and Stripe integration. Handles the full billing lifecycle from checkout through renewal, with production-grade webhook security.

## Architecture

```
User
  │
  ├── POST /api/v1/billing/checkout/  → Create Stripe Checkout Session
  │     │
  │     ▼
  │   Stripe Checkout (hosted page)
  │     │
  │     ▼
  │   POST /api/v1/billing/webhook/   → Stripe Webhook (signed)
  │     │
  │     ├── Signature verification (stripe-signature header)
  │     ├── Replay protection (reject events > 5 min old)
  │     ├── Idempotency (BillingEvent dedup by stripe_event_id)
  │     ├── Atomic transaction processing
  │     └── Audit logging (compliance app)
  │
  └── GET /api/v1/billing/subscription/  → Current plan + usage
```

## Models

| Model | Purpose |
|---|---|
| `Subscription` | 1:1 with User. Stores Stripe customer/subscription IDs, plan, status (trialing/active/past_due/canceled), and period dates. |
| `Invoice` | Stripe invoice records linked to subscription. Stores amount, currency, PDF link, and period. |
| `UsageRecord` | Tracks usage against plan limits per billing period. Metrics: pageviews, audits, AI calls, leads. |
| `BillingEvent` | Idempotency guard + audit trail for Stripe webhooks. Every incoming event is recorded before processing; duplicate `stripe_event_id` values are rejected. |

## Webhook Security (`webhooks.py`)

Six layers of hardening:

1. **Signature verification** — `stripe.Webhook.construct_event()` validates the `Stripe-Signature` header.
2. **Idempotency** — `BillingEvent` with unique `stripe_event_id` prevents double-processing from retries.
3. **Replay protection** — Events older than 5 minutes (`MAX_EVENT_AGE_SECONDS = 300`) are rejected.
4. **Atomic transactions** — Event processing runs inside `transaction.atomic()`.
5. **Smart error codes** — Database errors return 500 (Stripe retries); business logic errors return 200 (no retry).
6. **Audit trail** — Every webhook (success or failure) is logged via `audit_log()` for SOC 2 compliance.

## Event Routing

| Stripe Event | Handler |
|---|---|
| `checkout.session.completed` | `StripeService.handle_checkout_completed` |
| `customer.subscription.updated` | `StripeService.handle_subscription_updated` |
| `customer.subscription.deleted` | `StripeService.handle_subscription_updated` |
| `invoice.paid` | `StripeService.handle_invoice_paid` |
| `invoice.payment_failed` | `StripeService.handle_invoice_payment_failed` |
| `customer.subscription.trial_will_end` | Internal trial-ending handler |

## Middleware

The billing app includes middleware for enforcing plan limits at the API level (e.g., blocking requests when usage exceeds plan quotas).

## Key Design Decisions

- **Stripe as source of truth** — Subscription state is synced from Stripe via webhooks. The local `Subscription` model is a read cache.
- **Event sourcing** — `BillingEvent` stores the full webhook payload, enabling replay and debugging.
- **Usage metering** — `UsageRecord` is updated incrementally by other apps (analytics pixel, lead creation, audit runs) against the current billing period.

## Dependencies

- **Depends on:** `accounts`, `core` (encryption, audit logging)
- **External:** Stripe API
