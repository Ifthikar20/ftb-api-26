"""Celery configuration for GrowthPilot."""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("growthpilot")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ── Queue topology ──
# Slow third-party API calls must not block pixel/analytics aggregation.
#   default      — analytics, pixel, accounts (fast, in-process work)
#   integrations — HubSpot, Semrush, Google Ads, OAuth token refresh
#   webhooks     — outbound webhook delivery (user-controlled URLs, slow, isolated)
#   ai           — LLM ranking
app.conf.task_default_queue = "default"
app.conf.task_routes = {
    # webhooks
    "apps.websites.tasks.deliver_webhook": {"queue": "webhooks"},
    # integrations / OAuth
    "apps.websites.tasks.refresh_expiring_tokens": {"queue": "integrations"},
    # AI / LLM
    "apps.llm_ranking.tasks.*": {"queue": "ai"},
    "apps.citations.tasks.*": {"queue": "ai"},
    "apps.brand_vault.tasks.*": {"queue": "ai"},
    "apps.claim_verifier.tasks.*": {"queue": "ai"},
    "apps.content_studio.tasks.*": {"queue": "ai"},
}

app.conf.beat_schedule = {
    # ── Daily ──
    "expire-sessions": {
        "task": "apps.accounts.tasks.expire_inactive_sessions",
        "schedule": crontab(minute=0, hour=3),
    },
    # ── Weekly ──
    "weekly-reports": {
        "task": "apps.notifications.tasks.send_weekly_reports",
        "schedule": crontab(minute=0, hour=9, day_of_week=1),
    },
    # ── Hourly ──
    "analytics-aggregation": {
        "task": "apps.analytics.tasks.aggregate_hourly_metrics",
        "schedule": crontab(minute=5),
    },
    # ── Every 15 minutes ──
    "refresh-expiring-oauth-tokens": {
        "task": "apps.websites.tasks.refresh_expiring_tokens",
        "schedule": crontab(minute="*/15"),
    },
    # ── Monthly ──
    "hard-delete-expired": {
        "task": "core.tasks.hard_delete_soft_deleted",
        "schedule": crontab(minute=0, hour=0, day_of_month=1),
    },
    "rotate-encryption-keys": {
        "task": "core.tasks.check_encryption_key_rotation",
        "schedule": crontab(minute=0, hour=0, day_of_month=1),
    },
    # ── Integration Reports ──
    "daily-growth-reports": {
        "task": "apps.notifications.tasks.send_daily_growth_reports",
        "schedule": crontab(minute=0, hour=9),  # 9 AM daily
    },
    # ── LLM Ranking ──
    "llm-ranking-schedule-dispatcher": {
        "task": "apps.llm_ranking.tasks.dispatch_scheduled_audits",
        "schedule": crontab(minute="*/15"),  # Every 15 min — checks next_run_at
    },
    # ── Prompt Library ──
    "mine-daily-prompts": {
        "task": "apps.prompt_library.tasks.mine_daily_prompts",
        "schedule": crontab(minute=0, hour=4),
    },
    "compute-demand-scores": {
        "task": "apps.prompt_library.tasks.compute_demand_scores",
        "schedule": crontab(minute=0, hour=5),
    },
    # ── Citations / Source Influence ──
    "compute-source-influence": {
        "task": "apps.citations.tasks.compute_source_influence_snapshots",
        "schedule": crontab(minute=30, hour=5),
    },
    "classify-unknown-domains": {
        "task": "apps.citations.tasks.classify_unknown_domains",
        "schedule": crontab(minute=0, hour=6),
    },
    # ── Brand Vault ──
    "refresh-fact-embeddings": {
        "task": "apps.brand_vault.tasks.refresh_fact_embeddings",
        "schedule": crontab(minute=30, hour=3),
    },
    # ── Content Studio ──
    "generate-briefs-daily": {
        "task": "apps.content_studio.tasks.generate_briefs_daily",
        "schedule": crontab(minute=15, hour=6),
    },
}
