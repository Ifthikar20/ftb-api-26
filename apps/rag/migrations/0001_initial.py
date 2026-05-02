import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("websites", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeSource",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("url", models.URLField(max_length=2000)),
                ("title", models.CharField(blank=True, max_length=500)),
                ("kind", models.CharField(
                    choices=[
                        ("homepage", "Homepage"),
                        ("blog", "Blog post"),
                        ("product", "Product page"),
                        ("docs", "Documentation"),
                        ("review", "Review / mention"),
                        ("other", "Other"),
                        ("audit_context", "Audit context"),
                    ],
                    db_index=True, default="other", max_length=20,
                )),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("ingesting", "Ingesting"),
                        ("ready", "Ready"),
                        ("failed", "Failed"),
                    ],
                    db_index=True, default="pending", max_length=20,
                )),
                ("content_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("chunk_count", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("last_ingested_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="knowledge_sources",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="knowledge_sources",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "rag_knowledge_source",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="knowledgesource",
            constraint=models.UniqueConstraint(
                fields=("user", "website", "url"),
                name="uq_rag_source_user_website_url",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgesource",
            index=models.Index(
                fields=["user", "website"],
                name="rag_kn_sou_user_website_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgesource",
            index=models.Index(
                fields=["website", "kind"],
                name="rag_kn_sou_website_kind_idx",
            ),
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("chunk_index", models.IntegerField(default=0)),
                ("text", models.TextField()),
                ("embedding", models.JSONField(default=list)),
                ("embedding_model", models.CharField(blank=True, max_length=100)),
                ("embedding_dim", models.IntegerField(default=0)),
                ("section_label", models.CharField(blank=True, max_length=200)),
                ("token_count", models.IntegerField(default=0)),
                ("source", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="chunks",
                    to="rag.knowledgesource",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="knowledge_chunks",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("website", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="knowledge_chunks",
                    to="websites.website",
                )),
            ],
            options={
                "db_table": "rag_knowledge_chunk",
                "ordering": ["source", "chunk_index"],
            },
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=models.Index(
                fields=["user", "website"],
                name="rag_kn_chk_user_website_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=models.Index(
                fields=["source", "chunk_index"],
                name="rag_kn_chk_source_idx_idx",
            ),
        ),
    ]
