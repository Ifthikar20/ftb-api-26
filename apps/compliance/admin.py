"""
Django admin interface for compliance audit logs.

Read-only admin for SOC 2 auditors and compliance officers to query
the audit trail without direct database access.
"""

from django.contrib import admin

from apps.compliance.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "event",
        "action",
        "user_email",
        "resource_type",
        "resource_id",
        "method",
        "path",
        "status_code",
        "success",
        "duration_ms",
    ]
    list_filter = ["action", "success", "event", "resource_type"]
    search_fields = ["user_email", "event", "resource_id", "path", "request_id"]
    readonly_fields = [
        "id",
        "timestamp",
        "event",
        "action",
        "user_id",
        "user_email",
        "ip_address",
        "user_agent",
        "resource_type",
        "resource_id",
        "method",
        "path",
        "request_id",
        "status_code",
        "duration_ms",
        "metadata",
        "success",
        "error_message",
    ]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
