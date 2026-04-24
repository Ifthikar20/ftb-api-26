from rest_framework import serializers

from apps.websites.models import Website, WebsiteMembership, WebsiteSettings


class WebsiteSerializer(serializers.ModelSerializer):
    pixel_snippet = serializers.SerializerMethodField()

    class Meta:
        model = Website
        fields = [
            "id", "url", "name", "industry", "description", "topics",
            "platform_type", "onboarding_completed",
            "pixel_key", "pixel_verified", "pixel_verified_at", "crawl_status",
            "is_active", "pixel_snippet", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "pixel_key", "pixel_verified", "pixel_verified_at", "crawl_status"]

    def get_pixel_snippet(self, obj):
        return f'<script src="https://fetchbot.ai/pixel/growthpilot.min.js" data-key="{obj.pixel_key}"></script>'


class WebsiteCreateSerializer(serializers.Serializer):
    url = serializers.URLField()
    name = serializers.CharField(max_length=200)
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    platform_type = serializers.ChoiceField(
        choices=["shopify", "wordpress", "woocommerce", "custom"],
        required=False, default="custom"
    )


class WebsiteUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    industry = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    topics = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        default=list,
    )
    onboarding_completed = serializers.BooleanField(required=False)


class WebsiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSettings
        fields = ["track_anonymous", "notify_hot_leads", "hot_lead_threshold", "weekly_report"]


class WebsiteMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = WebsiteMembership
        fields = ["id", "user_email", "user_name", "role", "accepted", "created_at"]
        read_only_fields = ["id", "user_email", "user_name", "accepted", "created_at"]
