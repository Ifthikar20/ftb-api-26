"""Initial schema for the prompt_library app."""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("llm_ranking", "0014_schedule_resilience"),
    ]

    operations = [
        migrations.CreateModel(
            name="Industry",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "prompt_library_industry", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Prompt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("intent_bucket", models.CharField(choices=[("category", "Category"), ("comparison", "Comparison"), ("problem", "Problem"), ("local", "Local")], max_length=20)),
                ("language", models.CharField(default="en", max_length=8)),
                ("source", models.CharField(choices=[("reddit", "Reddit"), ("quora", "Quora"), ("serpapi", "SerpAPI"), ("dataforseo", "DataForSEO"), ("llm_synth", "LLM Synthesis"), ("gsc_aggregate", "GSC Aggregate"), ("manual", "Manual")], max_length=20)),
                ("source_url", models.URLField(blank=True, max_length=500)),
                ("demand_score", models.FloatField(db_index=True, default=0.0)),
                ("is_active", models.BooleanField(default=True)),
                ("text_hash", models.CharField(db_index=True, max_length=64)),
                ("industry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prompts", to="prompt_library.industry")),
            ],
            options={
                "db_table": "prompt_library_prompt",
                "ordering": ["-demand_score", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="prompt",
            index=models.Index(fields=["industry", "intent_bucket", "is_active"], name="pl_prompt_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="prompt",
            unique_together={("industry", "text_hash")},
        ),
        migrations.CreateModel(
            name="PromptVariation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("text_hash", models.CharField(max_length=64)),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("embedding_model", models.CharField(blank=True, max_length=64)),
                ("parent_prompt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variations", to="prompt_library.prompt")),
            ],
            options={"db_table": "prompt_library_promptvariation"},
        ),
        migrations.AlterUniqueTogether(
            name="promptvariation",
            unique_together={("parent_prompt", "text_hash")},
        ),
        migrations.CreateModel(
            name="PromptSampleRun",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("seed", models.IntegerField()),
                ("strategy", models.CharField(default="stratified", max_length=32)),
                ("audit_run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="prompt_sample_run", to="llm_ranking.llmrankingaudit")),
                ("industry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="prompt_library.industry")),
            ],
            options={"db_table": "prompt_library_promptsamplerun", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PromptSampleEntry",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("rank", models.IntegerField()),
                ("prompt", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="prompt_library.prompt")),
                ("sample_run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="prompt_library.promptsamplerun")),
            ],
            options={"db_table": "prompt_library_promptsampleentry", "ordering": ["rank"]},
        ),
        migrations.AlterUniqueTogether(
            name="promptsampleentry",
            unique_together={("sample_run", "prompt")},
        ),
        migrations.AddField(
            model_name="promptsamplerun",
            name="sampled_prompts",
            field=models.ManyToManyField(related_name="sample_runs", through="prompt_library.PromptSampleEntry", to="prompt_library.prompt"),
        ),
    ]
