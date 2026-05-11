"""Initial schema for the content_studio app."""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("websites", "0001_initial"),
        ("prompt_library", "0001_initial"),
        ("brand_vault", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentBrief",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("gap_type", models.CharField(
                    choices=[
                        ("visibility", "Visibility"),
                        ("accuracy", "Accuracy"),
                        ("citation", "Citation"),
                    ],
                    max_length=16,
                )),
                ("impact_score", models.FloatField(db_index=True, default=0.0)),
                ("target_format", models.CharField(
                    choices=[
                        ("blog", "Blog"),
                        ("faq", "FAQ"),
                        ("reddit_answer", "Reddit answer"),
                        ("json_ld", "JSON-LD"),
                        ("landing_page", "Landing page"),
                        ("meta_description", "Meta description"),
                    ],
                    max_length=20,
                )),
                ("target_source_class", models.CharField(blank=True, max_length=24)),
                ("headline", models.CharField(max_length=300)),
                ("description", models.TextField()),
                ("suggested_structure", models.JSONField(default=dict)),
                ("target_keywords", models.JSONField(default=list)),
                ("dedupe_key", models.CharField(blank=True, db_index=True, max_length=128)),
                ("status", models.CharField(
                    choices=[
                        ("open", "Open"),
                        ("drafted", "Drafted"),
                        ("skipped", "Skipped"),
                        ("expired", "Expired"),
                    ],
                    db_index=True, default="open", max_length=12,
                )),
                ("grounded_facts", models.ManyToManyField(
                    blank=True, related_name="briefs", to="brand_vault.brandfact",
                )),
                ("target_prompt", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="briefs", to="prompt_library.prompt",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="briefs", to="websites.website",
                )),
            ],
            options={
                "db_table": "content_studio_contentbrief",
                "ordering": ["-impact_score", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contentbrief",
            index=models.Index(
                fields=["website", "status", "-impact_score"],
                name="cs_brief_w_s_imp_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contentbrief",
            index=models.Index(
                fields=["website", "gap_type"],
                name="cs_brief_w_gap_idx",
            ),
        ),
        migrations.CreateModel(
            name="ContentDraft",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=400)),
                ("body_markdown", models.TextField()),
                ("body_html", models.TextField(blank=True)),
                ("json_ld", models.JSONField(blank=True, null=True)),
                ("word_count", models.IntegerField(default=0)),
                ("voice_score", models.FloatField(blank=True, null=True)),
                ("accuracy_score", models.FloatField(blank=True, null=True)),
                ("voice_notes", models.TextField(blank=True)),
                ("accuracy_notes", models.TextField(blank=True)),
                ("status", models.CharField(
                    choices=[
                        ("generating", "Generating"),
                        ("ready", "Ready"),
                        ("edited", "Edited"),
                        ("approved", "Approved"),
                        ("published", "Published"),
                        ("archived", "Archived"),
                    ],
                    db_index=True, default="generating", max_length=12,
                )),
                ("generated_by", models.CharField(default="anthropic", max_length=24)),
                ("revision", models.IntegerField(default=1)),
                ("brief", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="drafts", to="content_studio.contentbrief",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="drafts", to="websites.website",
                )),
            ],
            options={
                "db_table": "content_studio_contentdraft",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contentdraft",
            index=models.Index(
                fields=["website", "status"], name="cs_draft_w_s_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contentdraft",
            index=models.Index(
                fields=["brief"], name="cs_draft_brief_idx",
            ),
        ),
        migrations.CreateModel(
            name="PublishTarget",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(
                    choices=[
                        ("wordpress", "WordPress"),
                        ("webflow", "Webflow"),
                        ("shopify", "Shopify"),
                        ("hubspot", "HubSpot"),
                        ("manual", "Manual export"),
                    ],
                    max_length=16,
                )),
                ("label", models.CharField(blank=True, max_length=120)),
                ("config", models.JSONField(default=dict)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="publish_targets", to="websites.website",
                )),
            ],
            options={
                "db_table": "content_studio_publishtarget",
                "unique_together": {("website", "provider", "label")},
            },
        ),
        migrations.CreateModel(
            name="PublishLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("queued", "Queued"),
                        ("published", "Published"),
                        ("failed", "Failed"),
                    ],
                    default="pending", max_length=12,
                )),
                ("external_id", models.CharField(blank=True, max_length=200)),
                ("external_url", models.URLField(blank=True, max_length=1000)),
                ("error_message", models.TextField(blank=True)),
                ("request_payload", models.JSONField(default=dict)),
                ("response_payload", models.JSONField(default=dict)),
                ("draft", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="publish_logs", to="content_studio.contentdraft",
                )),
                ("target", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to="content_studio.publishtarget",
                )),
            ],
            options={
                "db_table": "content_studio_publishlog",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ROIAttribution",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("measured_at", models.DateTimeField()),
                ("days_since_publish", models.IntegerField()),
                ("visibility_before", models.FloatField(blank=True, null=True)),
                ("visibility_after", models.FloatField(blank=True, null=True)),
                ("visibility_lift", models.FloatField(blank=True, null=True)),
                ("citation_count_before", models.IntegerField(default=0)),
                ("citation_count_after", models.IntegerField(default=0)),
                ("accuracy_lift", models.FloatField(blank=True, null=True)),
                ("affected_prompts", models.JSONField(default=list)),
                ("draft", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="roi_records", to="content_studio.contentdraft",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="roi_records", to="websites.website",
                )),
            ],
            options={
                "db_table": "content_studio_roiattribution",
                "ordering": ["-measured_at"],
            },
        ),
    ]
