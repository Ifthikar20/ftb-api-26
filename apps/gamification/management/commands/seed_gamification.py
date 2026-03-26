"""Seed the initial gamification milestones and collectible cards."""

from django.core.management.base import BaseCommand
from apps.gamification.models import GrowthMilestone, CollectibleCard


MILESTONES = [
    # Common (10 pts)
    {
        "key": "first_audit",
        "title": "First Audit",
        "description": "Complete your first site audit",
        "card": {
            "name": "Scout Ranger",
            "description": "Every journey begins with a single step. You ran your first site audit!",
            "image": "/images/cards/scout-ranger.png",
            "rarity": "common",
            "point_value": 10,
        },
    },
    {
        "key": "first_keyword",
        "title": "First Keyword",
        "description": "Track your first keyword",
        "card": {
            "name": "Word Seeker",
            "description": "You've begun tracking keywords. The data hunt is on!",
            "image": "/images/cards/word-seeker.png",
            "rarity": "common",
            "point_value": 10,
        },
    },
    # Rare (25 pts)
    {
        "key": "first_lead",
        "title": "First Lead",
        "description": "Get your first hot lead",
        "card": {
            "name": "Lead Hunter",
            "description": "Your first hot lead found. The pipeline is warming up!",
            "image": "/images/cards/lead-hunter.png",
            "rarity": "rare",
            "point_value": 25,
        },
    },
    {
        "key": "visitors_100",
        "title": "100 Visitors",
        "description": "Reach 100 total visitors",
        "card": {
            "name": "Crowd Gatherer",
            "description": "100 visitors and counting. Your presence is growing!",
            "image": "/images/cards/crowd-gatherer.png",
            "rarity": "rare",
            "point_value": 25,
        },
    },
    # Epic (50 pts)
    {
        "key": "visitors_1k",
        "title": "1K Visitors",
        "description": "Reach 1,000 total visitors",
        "card": {
            "name": "Traffic Titan",
            "description": "A thousand visitors bow before your content. Impressive!",
            "image": "/images/cards/traffic-titan.png",
            "rarity": "epic",
            "point_value": 50,
        },
    },
    {
        "key": "leads_50",
        "title": "50 Hot Leads",
        "description": "Get 50 hot leads",
        "card": {
            "name": "Pipeline Master",
            "description": "50 hot leads! Your pipeline is a force of nature.",
            "image": "/images/cards/pipeline-master.png",
            "rarity": "epic",
            "point_value": 50,
        },
    },
    # Legendary (100 pts)
    {
        "key": "visitors_10k",
        "title": "10K Visitors",
        "description": "Reach 10,000 total visitors",
        "card": {
            "name": "Growth Dragon",
            "description": "10,000 visitors! You've achieved legendary growth.",
            "image": "/images/cards/growth-dragon.png",
            "rarity": "legendary",
            "point_value": 100,
        },
    },
    {
        "key": "perfect_audit",
        "title": "Perfect Audit",
        "description": "Score 100/100 on a site audit",
        "card": {
            "name": "Perfection Knight",
            "description": "A flawless 100/100 audit score. You are the standard.",
            "image": "/images/cards/perfection-knight.png",
            "rarity": "legendary",
            "point_value": 100,
        },
    },
]


class Command(BaseCommand):
    help = "Seed gamification milestones and collectible cards"

    def handle(self, *args, **options):
        created_milestones = 0
        created_cards = 0

        for data in MILESTONES:
            milestone, m_created = GrowthMilestone.objects.get_or_create(
                key=data["key"],
                defaults={
                    "title": data["title"],
                    "description": data["description"],
                },
            )
            if m_created:
                created_milestones += 1

            card_data = data["card"]
            card, c_created = CollectibleCard.objects.get_or_create(
                milestone=milestone,
                defaults={
                    "name": card_data["name"],
                    "description": card_data["description"],
                    "image": card_data["image"],
                    "rarity": card_data["rarity"],
                    "point_value": card_data["point_value"],
                },
            )
            if c_created:
                created_cards += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_milestones} milestones, {created_cards} cards"
            )
        )
