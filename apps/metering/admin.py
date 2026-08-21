from django.contrib import admin

from apps.metering.models import PolarCustomer, PolarEventOutbox


@admin.register(PolarEventOutbox)
class PolarEventOutboxAdmin(admin.ModelAdmin):
    list_display = (
        "idempotency_key",
        "name",
        "external_customer_id",
        "status",
        "attempts",
        "next_attempt_at",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "name")
    search_fields = ("idempotency_key", "external_customer_id", "last_error")
    readonly_fields = [f.name for f in PolarEventOutbox._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(PolarCustomer)
class PolarCustomerAdmin(admin.ModelAdmin):
    list_display = ("user", "polar_customer_id", "environment", "synced_at", "created_at")
    search_fields = ("user__email", "polar_customer_id")
    readonly_fields = ("user", "polar_customer_id", "environment", "synced_at")
