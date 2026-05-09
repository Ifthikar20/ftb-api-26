"""Add ToneSample model for brand voice modeling (Phase 4 prerequisite)."""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websites", "0001_initial"),
        ("rag", "0001_initial"),
        ("brand_vault", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ToneSample",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("text_hash", models.CharField(db_index=True, max_length=64)),
                ("word_count", models.IntegerField(default=0)),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("source_chunk", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="tone_samples", to="rag.knowledgechunk",
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="tone_samples", to="websites.website",
                )),
            ],
            options={"db_table": "brand_vault_tonesample"},
        ),
        migrations.AddIndex(
            model_name="tonesample",
            index=models.Index(fields=["website"], name="bv_tone_w_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="tonesample",
            unique_together={("website", "text_hash")},
        ),
    ]
