from rest_framework import serializers
from apps.gamification.models import CollectibleCard, UserCard


class CollectibleCardSerializer(serializers.ModelSerializer):
    earned = serializers.BooleanField(read_only=True, default=False)
    milestone_title = serializers.CharField(source="milestone.title", default="", read_only=True)

    class Meta:
        model = CollectibleCard
        fields = [
            "id", "name", "description", "image",
            "rarity", "point_value", "earned", "milestone_title",
        ]


class UserCardSerializer(serializers.ModelSerializer):
    card = CollectibleCardSerializer(read_only=True)

    class Meta:
        model = UserCard
        fields = ["id", "card", "earned_at", "is_new"]


class ProgressSerializer(serializers.Serializer):
    total_points = serializers.IntegerField()
    current_level = serializers.IntegerField()
    cards_collected = serializers.IntegerField()
    next_level_points = serializers.IntegerField()
    progress_pct = serializers.IntegerField()
