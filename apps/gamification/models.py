import uuid
from django.conf import settings
from django.db import models


class GrowthMilestone(models.Model):
    """Defines a growth trigger that awards a collectible card."""

    key = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class CollectibleCard(models.Model):
    """A collectible card with pixel art, rarity, and point value."""

    class Rarity(models.TextChoices):
        COMMON = "common", "Common"
        RARE = "rare", "Rare"
        EPIC = "epic", "Epic"
        LEGENDARY = "legendary", "Legendary"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    image = models.CharField(max_length=256, blank=True, default="", help_text="Path under /images/cards/")
    rarity = models.CharField(max_length=16, choices=Rarity.choices, default=Rarity.COMMON)
    point_value = models.PositiveIntegerField(default=10)
    milestone = models.OneToOneField(
        GrowthMilestone,
        on_delete=models.CASCADE,
        related_name="card",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rarity", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"


class UserCard(models.Model):
    """Join table: user has earned a card."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collected_cards",
    )
    card = models.ForeignKey(
        CollectibleCard,
        on_delete=models.CASCADE,
        related_name="owners",
    )
    earned_at = models.DateTimeField(auto_now_add=True)
    is_new = models.BooleanField(default=True, help_text="Unseen by user")

    class Meta:
        unique_together = ("user", "card")
        ordering = ["-earned_at"]

    def __str__(self):
        return f"{self.user} → {self.card.name}"


class UserProgress(models.Model):
    """Aggregate gamification stats for a user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gamification_progress",
    )
    total_points = models.PositiveIntegerField(default=0)
    current_level = models.PositiveIntegerField(default=1)
    cards_collected = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "User progress"

    def __str__(self):
        return f"{self.user} — Level {self.current_level} ({self.total_points} pts)"
