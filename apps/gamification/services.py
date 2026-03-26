from django.conf import settings
from django.utils import timezone

from .models import CollectibleCard, GrowthMilestone, UserCard, UserProgress


def is_gamification_enabled() -> bool:
    """Check if gamification feature is enabled."""
    return getattr(settings, "GAMIFICATION_ENABLED", True)


def get_or_create_progress(user) -> UserProgress:
    progress, _ = UserProgress.objects.get_or_create(user=user)
    return progress


def _compute_level(points: int) -> int:
    """Simple level formula: every 100 pts = 1 level, min 1."""
    return max(1, (points // 100) + 1)


def check_and_award(user, milestone_key: str) -> UserCard | None:
    """
    Check if the user qualifies for a milestone and award the card.
    Returns the UserCard if newly awarded, None otherwise.
    """
    if not is_gamification_enabled():
        return None

    try:
        milestone = GrowthMilestone.objects.select_related("card").get(key=milestone_key)
    except GrowthMilestone.DoesNotExist:
        return None

    card = getattr(milestone, "card", None)
    if card is None:
        return None

    # Already earned?
    if UserCard.objects.filter(user=user, card=card).exists():
        return None

    # Award it
    user_card = UserCard.objects.create(user=user, card=card)

    # Update progress
    progress = get_or_create_progress(user)
    progress.total_points += card.point_value
    progress.cards_collected += 1
    progress.current_level = _compute_level(progress.total_points)
    progress.save(update_fields=["total_points", "cards_collected", "current_level"])

    return user_card


def get_user_progress(user) -> dict:
    """Return gamification stats for a user."""
    progress = get_or_create_progress(user)
    next_level_pts = progress.current_level * 100
    return {
        "total_points": progress.total_points,
        "current_level": progress.current_level,
        "cards_collected": progress.cards_collected,
        "next_level_points": next_level_pts,
        "progress_pct": min(100, int((progress.total_points / next_level_pts) * 100)) if next_level_pts else 100,
    }


def get_card_collection(user) -> list[dict]:
    """Return all cards with earned status for a user."""
    all_cards = CollectibleCard.objects.all()
    earned_ids = set(
        UserCard.objects.filter(user=user).values_list("card_id", flat=True)
    )

    cards = []
    for card in all_cards:
        earned = card.id in earned_ids
        cards.append({
            "id": str(card.id),
            "name": card.name,
            "description": card.description,
            "image": card.image,
            "rarity": card.rarity,
            "point_value": card.point_value,
            "earned": earned,
            "milestone_title": card.milestone.title if card.milestone else "",
            "milestone_description": card.milestone.description if card.milestone else "",
        })

    return cards
