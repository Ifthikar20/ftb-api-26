from rest_framework import serializers


class OnboardingScanSerializer(serializers.Serializer):
    """Body of POST /api/v1/onboarding/scan/."""

    url = serializers.URLField(max_length=2000)

    def validate_url(self, value):
        # Defence in depth — the same SSRF guard is enforced inside
        # ``scan_domain``, but rejecting at the API edge is cleaner
        # (no Celery task fires, no ambiguous error message).
        from core.validators.url_safety import UnsafeURLError, assert_url_safe
        try:
            return assert_url_safe(value)
        except UnsafeURLError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class OnboardingSaveSerializer(serializers.Serializer):
    """Body of POST /api/v1/onboarding/save/."""

    url = serializers.URLField(max_length=2000)
    business_name = serializers.CharField(max_length=200)
    industry = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    # Optional UUID of an `apps.prompt_library.Industry` row. When supplied,
    # it takes precedence over the legacy free-text ``industry`` field —
    # the typeahead in the new onboarding flow sends this id.
    industry_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=600, required=False, default="", allow_blank=True)
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False, default=list, max_length=20,
    )
    competitors = serializers.ListField(
        child=serializers.DictField(),
        required=False, default=list, max_length=20,
    )

    def validate_url(self, value):
        from core.validators.url_safety import UnsafeURLError, assert_url_safe
        try:
            return assert_url_safe(value)
        except UnsafeURLError as exc:
            raise serializers.ValidationError(str(exc)) from exc
