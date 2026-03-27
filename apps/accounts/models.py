import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.mixins.timestamp_mixin import TimestampMixin
from core.utils.constants import Plan, Segment

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimestampMixin):
    """Custom user model with email-based auth and plan tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.STARTER)
    segment = models.CharField(
        max_length=20, choices=Segment.choices, default=Segment.INDIVIDUAL
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    onboarding_complete = models.BooleanField(default=False)
    last_daily_brief = models.DateField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""

    @property
    def effective_plan(self):
        """Return the plan to use for feature gating (org plan overrides personal plan for enterprise)."""
        if hasattr(self, "_org_cache"):
            return self._org_cache.plan
        membership = self.org_memberships.select_related("organization").first()
        if membership:
            self._org_cache = membership.organization
            return membership.organization.plan
        return self.plan


class Organization(TimestampMixin):
    """Enterprise organization — shared billing entity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_orgs")
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.ENTERPRISE)
    logo_url = models.URLField(blank=True)

    class Meta:
        db_table = "accounts_organization"

    def __str__(self):
        return self.name


class OrganizationMember(TimestampMixin):
    """Membership linking users to an organization."""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
        ("viewer", "Viewer"),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="org_memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    class Meta:
        db_table = "accounts_organizationmember"
        unique_together = [("organization", "user")]

    def __str__(self):
        return f"{self.user.email} → {self.organization.name} ({self.role})"


class UserProfile(TimestampMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar_url = models.URLField(blank=True)
    timezone = models.CharField(max_length=50, default="UTC")
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        db_table = "accounts_userprofile"

    def __str__(self):
        return f"Profile({self.user.email})"


class UserPreferences(TimestampMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    email_notifications = models.BooleanField(default=True)
    weekly_report = models.BooleanField(default=True)
    morning_brief = models.BooleanField(default=True)

    class Meta:
        db_table = "accounts_userpreferences"


class LoginAttempt(models.Model):
    """SOC2: Track all login attempts for audit and brute-force detection."""

    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    success = models.BooleanField(default=False)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="login_attempts"
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "accounts_loginattempt"
        indexes = [models.Index(fields=["email", "timestamp"])]

    def __str__(self):
        status = "success" if self.success else "failed"
        return f"LoginAttempt({self.email}, {status})"


class EmailVerificationOTP(models.Model):
    """6-digit OTP for email verification."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_otps")
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_emailverificationotp"


class PasswordResetToken(models.Model):
    """Secure token for password reset."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_passwordresettoken"
