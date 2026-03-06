from django.contrib import admin
from apps.billing.models import Subscription, Invoice, UsageRecord


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_end")
    list_filter = ("plan", "status")
    search_fields = ("user__email", "stripe_customer_id")
    readonly_fields = ("stripe_customer_id", "stripe_subscription_id")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("stripe_invoice_id", "subscription", "amount_paid", "status", "created_at")
    readonly_fields = ("stripe_invoice_id",)


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("subscription", "metric", "count", "period_start")
