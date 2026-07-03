from django.contrib import admin

from apps.search_console.models import GscDailyTotal, GscPageStat, GscQueryStat


@admin.register(GscDailyTotal)
class GscDailyTotalAdmin(admin.ModelAdmin):
    list_display = ("website", "date", "clicks", "impressions", "ctr", "position")
    list_filter = ("date",)
    search_fields = ("website__name", "website__url")


@admin.register(GscQueryStat)
class GscQueryStatAdmin(admin.ModelAdmin):
    list_display = ("website", "date", "query", "clicks", "impressions", "position")
    list_filter = ("date",)
    search_fields = ("query", "website__name")


@admin.register(GscPageStat)
class GscPageStatAdmin(admin.ModelAdmin):
    list_display = ("website", "date", "page", "clicks", "impressions", "position")
    list_filter = ("date",)
    search_fields = ("page", "website__name")
