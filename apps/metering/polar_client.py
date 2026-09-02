"""
Thin wrapper around the Polar.sh SDK — the ONLY module allowed to import
polar_sdk. Everything else in the codebase talks to Polar through these
functions so SDK surface changes stay contained here.

All calls run behind a shared Redis-backed circuit breaker (same class the
LLM providers use). Failures collapse into two exception types:

    PolarUnavailable — transient (network, 5xx, 408/429, breaker open).
                       Callers retry later; readers fall back to the
                       local ledger.
    PolarRejected    — permanent (validation / other 4xx). Retrying the
                       same payload can never succeed; outbox rows go
                       straight to dead status.

The client is None whenever POLAR_ACCESS_TOKEN is unset, so a Polar-less
install (tests, fresh dev) never attempts network calls.
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from core.resilience import CircuitBreaker

logger = logging.getLogger("metering.polar")

METER_TOKENS_NAME = "llm-tokens"
METER_SPEND_NAME = "ai-spend-micros"


class PolarUnavailable(Exception):
    """Transient Polar failure — retry later / fall back to local reads."""


class PolarRejected(Exception):
    """Permanent Polar rejection — the payload can never succeed."""


def is_configured() -> bool:
    return bool(settings.POLAR_ACCESS_TOKEN)


def get_client():
    """Lazy SDK client, or None when Polar is not configured."""
    if not is_configured():
        return None
    from polar_sdk import Polar

    server = "sandbox" if settings.POLAR_ENVIRONMENT == "sandbox" else "production"
    return Polar(access_token=settings.POLAR_ACCESS_TOKEN, server=server)


def breaker() -> CircuitBreaker:
    return CircuitBreaker(name="polar", failure_threshold=5, recovery_timeout=60)


def _translate(exc: Exception) -> Exception:
    """Map SDK/transport exceptions onto PolarUnavailable/PolarRejected."""
    try:
        from polar_sdk.models import PolarError
    except Exception:  # SDK missing entirely
        return PolarUnavailable(str(exc)[:300])

    if isinstance(exc, PolarError):
        status = getattr(getattr(exc, "raw_response", None), "status_code", None)
        if status is not None and 400 <= status < 500 and status not in (408, 429):
            return PolarRejected(f"HTTP {status}: {str(exc)[:300]}")
        return PolarUnavailable(str(exc)[:300])
    return PolarUnavailable(str(exc)[:300])


def _guarded(fn, *args, **kwargs):
    """Run one SDK call behind the breaker with error translation."""
    client = get_client()
    if client is None:
        raise PolarUnavailable("polar not configured")
    brk = breaker()
    if not brk.allow():
        raise PolarUnavailable("polar circuit open")
    try:
        result = fn(client, *args, **kwargs)
    except Exception as exc:
        translated = _translate(exc)
        # Only transient failures count toward opening the breaker —
        # a validation reject says nothing about Polar's availability.
        if isinstance(translated, PolarUnavailable):
            brk.record_failure()
        raise translated from exc
    brk.record_success()
    return result


# ── Events ────────────────────────────────────────────────────────────────


def ingest(events: list[dict]) -> tuple[int, int]:
    """Send a batch of event dicts. Returns (inserted, duplicates).

    Each dict must carry name/external_customer_id/metadata and an
    `external_id` (our idempotency key) — Polar deduplicates on it, so
    redelivering a batch after an ambiguous failure is safe.
    """
    if not events:
        return (0, 0)
    resp = _guarded(lambda c: c.events.ingest(request={"events": events}))
    inserted = getattr(resp, "inserted", 0)
    duplicates = getattr(resp, "duplicates", 0)
    return (inserted, duplicates)


# ── Customers ─────────────────────────────────────────────────────────────


def ensure_customer(user) -> str:
    """Create-or-fetch the Polar customer for ``user``; returns its Polar id.

    Uses external_id = str(user.id). Keeps the local PolarCustomer marker
    in sync (including after a sandbox -> production switch).
    """
    from apps.metering.models import PolarCustomer

    environment = settings.POLAR_ENVIRONMENT
    marker = PolarCustomer.objects.filter(user=user).first()
    if marker and marker.polar_customer_id and marker.environment == environment:
        return marker.polar_customer_id

    external_id = str(user.id)

    def _fetch(client):
        return client.customers.get_external(external_id=external_id)

    def _create(client):
        return client.customers.create(
            request={
                "email": user.email,
                "external_id": external_id,
                "name": (getattr(user, "get_full_name", lambda: "")() or user.email),
            }
        )

    try:
        customer = _guarded(_fetch)
    except PolarRejected as fetch_exc:
        # 404 — customer does not exist yet. A concurrent worker may win
        # the create race; that surfaces as a 422 on email/external_id
        # uniqueness, in which case the fetch succeeds on retry.
        try:
            customer = _guarded(_create)
        except PolarRejected as create_exc:
            try:
                customer = _guarded(_fetch)
            except PolarRejected:
                # The customer genuinely cannot be created (e.g. Polar
                # rejects undeliverable email domains like example.com).
                # Surface the CREATE error — the re-fetch 404 would mask
                # the actionable validation detail.
                raise create_exc from fetch_exc

    polar_id = str(customer.id)
    PolarCustomer.objects.update_or_create(
        user=user,
        defaults={
            "polar_customer_id": polar_id,
            "environment": environment,
            "synced_at": timezone.now(),
        },
    )
    return polar_id


# ── Meters ────────────────────────────────────────────────────────────────


def meter_quantities(
    meter_id: str,
    *,
    start: datetime,
    end: datetime,
    interval: str = "day",
    external_customer_id: str | None = None,
    tz: str = "UTC",
):
    """Time-bucketed usage for one meter. Returns the SDK response object
    (`.quantities` list of {timestamp, quantity} + `.total`)."""

    def _call(client):
        kwargs = {
            "id": meter_id,
            "start_timestamp": start,
            "end_timestamp": end,
            "interval": interval,
            "timezone": tz,
        }
        if external_customer_id:
            kwargs["external_customer_id"] = external_customer_id
        return client.meters.quantities(**kwargs)

    return _guarded(_call)


# ── Billing (products / checkout / portal / subscriptions) ────────────────
# Kept here so polar_sdk stays confined to this module. Orchestration
# lives in apps.billing.services.polar_billing.


def list_products():
    """All non-archived products for the org (first 100)."""
    page = _guarded(lambda c: c.products.list(page=1, limit=100, is_archived=False))
    return list(getattr(page.result, "items", []) or [])


def create_product(request: dict):
    return _guarded(lambda c: c.products.create(request=request))


def create_checkout(
    *,
    product_ids: list[str],
    external_customer_id: str,
    customer_email: str | None = None,
    success_url: str | None = None,
    metadata: dict | None = None,
    customer_ip_address: str | None = None,
):
    """Create a hosted checkout session; returns the Checkout object
    (redirect the customer to ``.url``).

    ``customer_ip_address`` matters: sessions are created from the
    backend, so without it Polar sees the server's IP and location-based
    currency/tax detection (we are on a Merchant of Record) misfires.
    """
    request: dict = {
        "products": product_ids,
        "external_customer_id": external_customer_id,
    }
    if customer_email:
        request["customer_email"] = customer_email
    if success_url:
        request["success_url"] = success_url
    if metadata:
        request["metadata"] = metadata
    if customer_ip_address:
        request["customer_ip_address"] = customer_ip_address
    return _guarded(lambda c: c.checkouts.create(request=request))


def get_checkout(checkout_id: str):
    return _guarded(lambda c: c.checkouts.get(id=checkout_id))


def get_customer_state(external_customer_id: str):
    """Customer + active subscriptions + benefits + meters in one object."""
    return _guarded(
        lambda c: c.customers.get_state_external(external_id=external_customer_id)
    )


def create_portal_url(external_customer_id: str, return_url: str | None = None) -> str:
    """Pre-authenticated hosted customer-portal URL for this user."""
    request: dict = {"external_customer_id": external_customer_id}
    if return_url:
        request["return_url"] = return_url
    session = _guarded(lambda c: c.customer_sessions.create(request=request))
    return str(session.customer_portal_url)


def update_subscription(subscription_id: str, updates: dict):
    return _guarded(
        lambda c: c.subscriptions.update(id=subscription_id, subscription_update=updates)
    )


def update_subscription_plan(
    subscription_id: str,
    *,
    end_trial_now: bool = False,
    product_id: str | None = None,
    proration_behavior: str | None = None,
):
    """PATCH plan-level subscription fields (end trial / switch product).

    Raw HTTP on purpose. Ending a trial immediately requires the REST
    literal ``"trial_end": "now"`` — a client-side timestamp is already in
    the past when Polar validates it ("Input should be in the future"),
    so "now" is the only race-free form. polar-sdk 0.32.0 cannot send it:
    it types trial_end as a datetime, and its update() re-validates dict
    input through the SubscriptionUpdate union, where ``{"trial_end":
    ...}`` mis-resolves to SubscriptionResume (``resume`` defaults True)
    and would silently send a resume request. Breaker + error translation
    mirror _guarded.
    """
    body: dict = {}
    if end_trial_now:
        body["trial_end"] = "now"
    if product_id:
        body["product_id"] = product_id
    if proration_behavior:
        body["proration_behavior"] = proration_behavior
    if not body:
        raise ValueError("update_subscription_plan called with nothing to update")

    if not is_configured():
        raise PolarUnavailable("polar not configured")
    brk = breaker()
    if not brk.allow():
        raise PolarUnavailable("polar circuit open")

    import httpx

    base = (
        "https://sandbox-api.polar.sh"
        if settings.POLAR_ENVIRONMENT == "sandbox"
        else "https://api.polar.sh"
    )
    try:
        resp = httpx.patch(
            f"{base}/v1/subscriptions/{subscription_id}",
            json=body,
            headers={"Authorization": f"Bearer {settings.POLAR_ACCESS_TOKEN}"},
            timeout=20.0,
        )
    except Exception as exc:
        brk.record_failure()
        raise PolarUnavailable(str(exc)[:300]) from exc
    if 400 <= resp.status_code < 500 and resp.status_code not in (408, 429):
        # Polar is reachable; the request itself was rejected. Like
        # _translate, a reject says nothing about availability.
        raise PolarRejected(f"HTTP {resp.status_code}: {resp.text[:300]}")
    if resp.status_code >= 500 or resp.status_code in (408, 429):
        brk.record_failure()
        raise PolarUnavailable(f"HTTP {resp.status_code}: {resp.text[:300]}")
    brk.record_success()
    return resp.json()


def get_subscription(subscription_id: str):
    """One subscription by id.

    Unlike customer state (whose subscriptions are only ever active or
    trialing) this carries the full status enum — past_due, unpaid,
    canceled, paused, incomplete_expired — so a vanished subscription can
    be mirrored with its REAL status. Scope: subscriptions:read.
    """
    return _guarded(lambda c: c.subscriptions.get(id=subscription_id))


class WebhookInvalid(Exception):
    """Webhook signature/payload failed verification."""


def validate_webhook(payload: bytes, headers: dict):
    """Verify a Polar webhook (Standard Webhooks signatures) and return
    the parsed event. Raises WebhookInvalid on any verification failure
    or when no secret is configured — unsigned payloads are never
    processed."""
    from django.conf import settings as dj_settings

    secret = dj_settings.POLAR_WEBHOOK_SECRET
    if not secret:
        raise WebhookInvalid("POLAR_WEBHOOK_SECRET is not configured")
    try:
        from polar_sdk.webhooks import WebhookVerificationError, validate_event
    except Exception as exc:  # SDK missing
        raise WebhookInvalid(f"polar_sdk unavailable: {exc}") from exc
    try:
        return validate_event(payload=payload, headers=headers, secret=secret)
    except WebhookVerificationError as exc:
        raise WebhookInvalid(str(exc)[:200]) from exc


def bootstrap_meters() -> dict[str, str]:
    """Create (or find) the two canonical meters; returns {name: meter_id}.

    Meters are immutable once they have processed events — the definitions
    below are final. Anything more granular (per-module, per-provider) is
    added later as NEW meters over the same `llm_usage` event stream.
    """
    event_name = settings.POLAR_EVENT_NAME
    wanted = {
        METER_TOKENS_NAME: {
            "name": METER_TOKENS_NAME,
            "filter": {
                "conjunction": "and",
                "clauses": [
                    {"property": "name", "operator": "eq", "value": event_name}
                ],
            },
            "aggregation": {"func": "sum", "property": "total_tokens"},
            "unit": "token",
        },
        METER_SPEND_NAME: {
            "name": METER_SPEND_NAME,
            "filter": {
                "conjunction": "and",
                "clauses": [
                    {"property": "name", "operator": "eq", "value": event_name}
                ],
            },
            "aggregation": {"func": "sum", "property": "cost_micros"},
            "unit": "custom",
            "custom_label": "micro-USD",
        },
    }

    existing = {}
    page = _guarded(lambda c: c.meters.list(page=1, limit=100))
    for meter in getattr(page.result, "items", []) or []:
        existing[meter.name] = str(meter.id)

    out = {}
    for name, request in wanted.items():
        if name in existing:
            out[name] = existing[name]
            continue
        created = _guarded(lambda c, r=request: c.meters.create(request=r))
        out[name] = str(created.id)
    return out
