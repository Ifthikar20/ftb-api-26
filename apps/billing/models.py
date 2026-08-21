from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin
from core.utils.constants import Plan, SubscriptionStatus


class Subscription(TimestampMixin):
    """Subscription record, managed by Polar (our billing provider).
    The Polar customer id lives on metering.PolarCustomer."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription"
    )
    polar_subscription_id = models.CharField(
        max_length=64, unique=True, blank=True, null=True, default=None
    )
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.INDIVIDUAL)
    status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    class Meta:
        db_table = "billing_subscription"

    def __str__(self):
        return f"Subscription({self.user.email}, {self.plan})"


class Invoice(TimestampMixin):
    """Invoice cache (populated from the billing provider's orders)."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="invoices")
    external_invoice_id = models.CharField(max_length=100, unique=True)
    amount_paid = models.IntegerField(default=0)  # Cents
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=20)
    invoice_pdf = models.URLField(blank=True)
    period_start = models.DateTimeField(null=True)
    period_end = models.DateTimeField(null=True)

    class Meta:
        db_table = "billing_invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice({self.external_invoice_id}, ${self.amount_paid / 100:.2f})"


class BillingEvent(TimestampMixin):
    """
    Idempotency guard + event sourcing audit trail for billing webhooks.

    Every incoming webhook writes an event record BEFORE processing.
    If the event_id already exists, the handler short-circuits. This
    prevents double-processing from provider retries or replay attacks.
    """

    event_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, default="")
    processing_time_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "billing_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["processed", "-created_at"]),
        ]

    def __str__(self):
        status = "OK" if self.processed else "PENDING"
        return f"BillingEvent({status} {self.event_type} {self.event_id})"
