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
#   default      — analytics, leads, pixel, accounts (fast, in-process work)
#   integrations — HubSpot, Semrush, Google Ads, OAuth token refresh
#   webhooks     — outbound webhook delivery (user-controlled URLs, slow, isolated)
#   ai           — LLM ranking, voice agent
app.conf.task_default_queue = "default"
app.conf.task_routes = {
    # webhooks
    "apps.websites.tasks.deliver_webhook": {"queue": "webhooks"},
    # integrations / OAuth
    "apps.websites.tasks.refresh_expiring_tokens": {"queue": "integrations"},
    "apps.competitors.tasks.*": {"queue": "integrations"},
    # AI / LLM
    "apps.llm_ranking.tasks.*": {"queue": "ai"},
    "apps.voice_agent.tasks.*": {"queue": "ai"},
    # Analytics scan + trend tasks (hit external APIs, can be slow)
    "apps.analytics.tasks.execute_keyword_scan": {"queue": "ai"},
    "apps.analytics.tasks.fetch_platform_trends": {"queue": "ai"},
}

app.conf.beat_schedule = {
    # ── Daily ──
    "daily-lead-rescoring": {
        "task": "apps.leads.tasks.rescore_all_leads",
        "schedule": crontab(minute=0, hour=2),
    },
    "expire-sessions": {
        "task": "apps.accounts.tasks.expire_inactive_sessions",
        "schedule": crontab(minute=0, hour=3),
    },
    # ── Weekly ──
    "competitor-crawl": {
        "task": "apps.competitors.tasks.crawl_all_competitors",
        "schedule": crontab(minute=0, hour=1, day_of_week=1),
    },
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
    # ── Voice Agent ──
    "voice-check-due-reminders": {
        "task": "apps.voice_agent.tasks.check_due_reminders",
        "schedule": crontab(minute="*/5"),
    },
    "voice-queue-health-check": {
        "task": "apps.voice_agent.tasks.queue_health_check",
        "schedule": crontab(minute="*/2"),
    },
    "voice-reconcile-monthly-usage": {
        "task": "apps.voice_agent.tasks.reconcile_monthly_usage",
        "schedule": crontab(minute=30, hour=3),  # 3:30 AM daily
    },
    # ── Keyword Intelligence ──
    "keyword-auto-scan-dispatcher": {
        "task": "apps.analytics.tasks.run_auto_keyword_scans",
        "schedule": crontab(minute="*/15"),  # Every 15 min — checks next_scan_at
    },
    "keyword-alert-check": {
        "task": "apps.analytics.tasks.check_keyword_alerts",
        "schedule": crontab(minute=0),  # Every hour
    },
    "platform-trend-fetch": {
        "task": "apps.analytics.tasks.fetch_platform_trends",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
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
}
