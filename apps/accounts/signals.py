from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User, UserPreferences, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create profile and preferences when a new user is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserPreferences.objects.get_or_create(user=instance)
