"""Celery configuration for GrowthPilot."""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("growthpilot")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # ── Daily ──
    "morning-brief": {
        "task": "apps.strategy.tasks.generate_morning_briefs",
        "schedule": crontab(minute=0, hour=6),
    },
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
    "scheduled-audits": {
        "task": "apps.audits.tasks.run_scheduled_audits",
        "schedule": crontab(minute=0, hour=4, day_of_week=1),
    },
    # ── Hourly ──
    "analytics-aggregation": {
        "task": "apps.analytics.tasks.aggregate_hourly_metrics",
        "schedule": crontab(minute=5),
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
}
