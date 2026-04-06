from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0004_rename_analytics_linkclick_link_clicked_idx_analytics_l_tracked_bdaa7e_idx_and_more"),
        ("websites", "0004_website_onboarding_completed_platform_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="KeywordScanConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_auto_scan_enabled", models.BooleanField(default=True)),
                ("scan_interval_hours", models.IntegerField(default=24)),
                ("scan_depth", models.IntegerField(default=5)),
                ("last_scanned_at", models.DateTimeField(blank=True, null=True)),
                ("next_scan_at", models.DateTimeField(blank=True, null=True)),
                ("total_scans", models.IntegerField(default=0)),
                ("website", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="keyword_scan_config",
                    to="websites.website",
                )),
            ],
            options={"db_table": "analytics_keywordscanconfig"},
        ),
        migrations.CreateModel(
            name="PlatformContent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("platform", models.CharField(
                    choices=[
                        ("linkedin", "LinkedIn"),
                        ("x", "X (Twitter)"),
                        ("facebook", "Facebook"),
                        ("instagram", "Instagram"),
                        ("blog", "Blog / Article"),
                        ("other", "Other"),
                    ],
                    default="linkedin",
                    max_length=20,
                )),
                ("title", models.CharField(blank=True, max_length=300)),
                ("content", models.TextField()),
                ("url", models.URLField(blank=True, max_length=2000)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("extracted_keywords", models.JSONField(default=list)),
                ("platform_post_id", models.CharField(blank=True, db_index=True, max_length=300)),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="platform_content",
                    to="websites.website",
                )),
            ],
            options={"db_table": "analytics_platformcontent", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="platformcontent",
            index=models.Index(fields=["website", "platform"], name="analytics_plat_website_platform_idx"),
        ),
    ]
