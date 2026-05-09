from django.contrib import admin

from apps.claim_verifier.models import Claim, ClaimMismatch


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("subject", "predicate", "audit", "website", "confidence")
    search_fields = ("subject", "predicate", "object", "text")


@admin.register(ClaimMismatch)
class ClaimMismatchAdmin(admin.ModelAdmin):
    list_display = ("claim", "mismatch_type", "severity", "dismissed", "created_at")
    list_filter = ("mismatch_type", "severity", "dismissed")
