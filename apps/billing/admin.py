from django.contrib import admin

from apps.billing.models import BillingEvent, Invoice, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_end", "polar_subscription_id")
    list_filter = ("plan", "status")
    search_fields = ("user__email", "polar_subscription_id")
    readonly_fields = ("polar_subscription_id",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("external_invoice_id", "subscription", "amount_paid", "status", "created_at")
    readonly_fields = ("external_invoice_id",)


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "processed", "processing_time_ms", "created_at")
    list_filter = ("processed", "event_type")
    search_fields = ("event_id",)
    readonly_fields = [f.name for f in BillingEvent._meta.fields]

    def has_add_permission(self, request):
        return False
