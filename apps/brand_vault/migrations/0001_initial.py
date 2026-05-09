"""Initial schema for the brand_vault app."""
import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("websites", "0001_initial"),
        ("rag", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BrandFact",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("subject", models.CharField(db_index=True, max_length=300)),
                ("predicate", models.CharField(db_index=True, max_length=200)),
                ("object", models.TextField()),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("extracted_by", models.CharField(default="llm", max_length=24)),
                ("confidence", models.FloatField(default=0.5)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending review"),
                        ("approved", "Approved"),
                        ("rejected", "Rejected"),
                        ("auto", "Auto-approved"),
                    ],
                    default="pending", max_length=12,
                )),
                ("version_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("version_to", models.DateTimeField(blank=True, null=True)),
                ("product_line", models.CharField(blank=True, max_length=120)),
                ("topic", models.CharField(blank=True, max_length=120)),
                ("audience", models.CharField(blank=True, max_length=120)),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("source_chunk", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="facts", to="rag.knowledgechunk",
                )),
                ("superseded_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="supersedes", to="brand_vault.brandfact",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="facts", to="websites.website",
                )),
            ],
            options={"db_table": "brand_vault_brandfact"},
        ),
        migrations.AddIndex(
            model_name="brandfact",
            index=models.Index(fields=["website", "status", "version_to"], name="bv_fact_w_st_vt_idx"),
        ),
        migrations.AddIndex(
            model_name="brandfact",
            index=models.Index(fields=["website", "subject", "predicate"], name="bv_fact_w_subj_pred_idx"),
        ),
        migrations.AddIndex(
            model_name="brandfact",
            index=models.Index(fields=["website", "product_line"], name="bv_fact_w_pl_idx"),
        ),
        migrations.CreateModel(
            name="FactRevision",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=24)),
                ("before", models.JSONField(default=dict)),
                ("after", models.JSONField(default=dict)),
                ("actor_user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ("fact", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="revisions", to="brand_vault.brandfact",
                )),
            ],
            options={"db_table": "brand_vault_factrevision", "ordering": ["-created_at"]},
        ),
    ]
