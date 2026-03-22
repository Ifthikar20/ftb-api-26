import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0002_trackedkeyword_keywordrankhistory"),
        ("leads", "0002_emailcampaign_campaignrecipient"),
        ("websites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrackedLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("destination_url", models.URLField(max_length=2000)),
                ("tracking_key", models.CharField(db_index=True, max_length=32, unique=True)),
                ("description", models.CharField(blank=True, max_length=300)),
                ("click_count", models.IntegerField(default=0)),
                ("conversion_count", models.IntegerField(default=0)),
                (
                    "campaign",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tracked_links",
                        to="leads.emailcampaign",
                    ),
                ),
                (
                    "website",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tracked_links",
                        to="websites.website",
                    ),
                ),
            ],
            options={"db_table": "analytics_trackedlink"},
        ),
        migrations.CreateModel(
            name="LinkClick",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
                ("user_agent", models.CharField(blank=True, max_length=500)),
                ("referrer", models.URLField(blank=True, max_length=2000)),
                ("clicked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("converted", models.BooleanField(db_index=True, default=False)),
                (
                    "tracked_link",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clicks",
                        to="analytics.trackedlink",
                    ),
                ),
                (
                    "visitor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="link_clicks",
                        to="analytics.visitor",
                    ),
                ),
                (
                    "campaign_recipient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="link_clicks",
                        to="leads.campaignrecipient",
                    ),
                ),
            ],
            options={"db_table": "analytics_linkclick"},
        ),
        migrations.AddIndex(
            model_name="linkclick",
            index=models.Index(fields=["tracked_link", "clicked_at"], name="analytics_linkclick_link_clicked_idx"),
        ),
    ]
