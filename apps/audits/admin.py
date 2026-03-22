from django.contrib import admin

from apps.audits.models import Audit, AuditIssue


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ("id", "website", "status", "overall_score", "triggered_at", "completed_at")
    list_filter = ("status",)
    readonly_fields = ("id", "triggered_at", "completed_at")


@admin.register(AuditIssue)
class AuditIssueAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "severity", "resolved", "audit")
    list_filter = ("severity", "category", "resolved")
