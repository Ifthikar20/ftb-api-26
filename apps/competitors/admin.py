from django.contrib import admin

from apps.competitors.models import Competitor, CompetitorChange, CompetitorSnapshot


@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ("name", "competitor_url", "website", "threat_level", "last_crawled_at")
    list_filter = ("threat_level", "auto_detected")


@admin.register(CompetitorSnapshot)
class CompetitorSnapshotAdmin(admin.ModelAdmin):
    list_display = ("competitor", "captured_at", "traffic_estimate")
    ordering = ["-captured_at"]


@admin.register(CompetitorChange)
class CompetitorChangeAdmin(admin.ModelAdmin):
    list_display = ("competitor", "change_type", "detected_at")
    ordering = ["-detected_at"]
