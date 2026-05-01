from decimal import Decimal

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User, UserProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds custom claims to the JWT payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["plan"] = user.plan
        return token


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=12, write_only=True)
    full_name = serializers.CharField(max_length=200)
    company_name = serializers.CharField(max_length=200, required=False, default="")

    def validate_email(self, value):
        return value.lower().strip()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=12, write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=12, write_only=True)


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.URLField(source="profile.avatar_url", required=False)
    timezone = serializers.CharField(source="profile.timezone", required=False)
    phone = serializers.CharField(source="profile.phone", required=False, allow_blank=True)
    bio = serializers.CharField(source="profile.bio", required=False, allow_blank=True)

    monthly_ai_cost_cap_usd = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        # DRF expects Decimal, not int, here — wrong type silently emits
        # a UserWarning at boot. Decimal('0') / Decimal('100000') are
        # cheap and shut the warning up.
        min_value=Decimal("0"),
        max_value=Decimal("100000"),
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "company_name", "plan",
            "is_email_verified", "onboarding_complete",
            "avatar_url", "timezone", "phone", "bio",
            "monthly_ai_cost_cap_usd",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "email", "plan", "is_email_verified", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        profile, _ = UserProfile.objects.get_or_create(user=instance)
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance
