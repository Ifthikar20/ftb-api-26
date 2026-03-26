from django.contrib import admin
from .models import GrowthMilestone, CollectibleCard, UserCard, UserProgress


@admin.register(GrowthMilestone)
class GrowthMilestoneAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "description")
    search_fields = ("key", "title")


@admin.register(CollectibleCard)
class CollectibleCardAdmin(admin.ModelAdmin):
    list_display = ("name", "rarity", "point_value", "milestone")
    list_filter = ("rarity",)
    search_fields = ("name",)


@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "earned_at", "is_new")
    list_filter = ("is_new", "card__rarity")
    raw_id_fields = ("user",)


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "total_points", "current_level", "cards_collected")
    raw_id_fields = ("user",)
