from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0005_keywordscanconfig_platformcontent"),
        ("websites", "0004_website_onboarding_completed_platform_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="KeywordAlert",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("threshold", models.IntegerField(default=3)),
                ("direction", models.CharField(
                    choices=[("any", "Any change"), ("improved", "Improved only"), ("declined", "Declined only")],
                    default="any", max_length=20,
                )),
                ("notification_method", models.CharField(
                    choices=[("email", "Email"), ("in_app", "In-app")],
                    default="email", max_length=20,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="keyword_alerts",
                    to="websites.website",
                )),
                ("tracked_keyword", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="alerts",
                    to="analytics.trackedkeyword",
                )),
            ],
            options={"db_table": "analytics_keywordalert"},
        ),
        migrations.CreateModel(
            name="KeywordAlertEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("keyword", models.CharField(max_length=300)),
                ("old_rank", models.IntegerField(blank=True, null=True)),
                ("new_rank", models.IntegerField(blank=True, null=True)),
                ("change", models.IntegerField()),
                ("triggered_at", models.DateTimeField(auto_now_add=True)),
                ("alert", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="analytics.keywordalert",
                )),
            ],
            options={"db_table": "analytics_keywordalertevent", "ordering": ["-triggered_at"]},
        ),
        migrations.CreateModel(
            name="CompetitorDomain",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("domain", models.CharField(max_length=300)),
                ("name", models.CharField(blank=True, max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="competitors",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "analytics_competitordomain",
                "unique_together": {("website", "domain")},
            },
        ),
        migrations.CreateModel(
            name="CompetitorKeywordRank",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("keyword", models.CharField(db_index=True, max_length=300)),
                ("rank", models.IntegerField(blank=True, null=True)),
                ("checked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("competitor", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ranks",
                    to="analytics.competitordomain",
                )),
            ],
            options={"db_table": "analytics_competitorkeywordrank", "ordering": ["-checked_at"]},
        ),
    ]
