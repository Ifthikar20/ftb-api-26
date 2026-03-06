from django.conf import settings
from django.db import models

from core.mixins.timestamp_mixin import TimestampMixin
from core.utils.constants import Plan, SubscriptionStatus


class Subscription(TimestampMixin):
    """Stripe subscription record."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription"
    )
    stripe_customer_id = models.CharField(max_length=100, unique=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.STARTER)
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
    """Stripe invoice record."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="invoices")
    stripe_invoice_id = models.CharField(max_length=100, unique=True)
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
        return f"Invoice({self.stripe_invoice_id}, ${self.amount_paid / 100:.2f})"


class UsageRecord(TimestampMixin):
    """Track usage against plan limits."""

    METRICS = [
        ("pageviews", "Page Views"),
        ("audits", "Audits"),
        ("ai_calls", "AI Calls"),
        ("leads", "Leads"),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="usage_records")
    metric = models.CharField(max_length=30, choices=METRICS)
    count = models.IntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        db_table = "billing_usagerecord"
        unique_together = [("subscription", "metric", "period_start")]

    def __str__(self):
        return f"Usage({self.metric}: {self.count})"
