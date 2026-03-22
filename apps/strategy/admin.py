from django.contrib import admin

from apps.strategy.models import Action, ContentCalendarEntry, MorningBrief, Strategy


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ("website", "plan_type", "status", "completion_pct", "generated_at")
    list_filter = ("status", "plan_type")


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ("title", "strategy", "status", "week_number", "due_date")
    list_filter = ("status",)


@admin.register(ContentCalendarEntry)
class ContentCalendarEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "website", "content_type", "scheduled_date", "status")
    list_filter = ("content_type", "status")


@admin.register(MorningBrief)
class MorningBriefAdmin(admin.ModelAdmin):
    list_display = ("website", "date", "created_at")
    ordering = ["-date"]
