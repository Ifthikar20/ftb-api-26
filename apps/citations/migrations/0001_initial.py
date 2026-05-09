"""Initial schema for the citations app."""
import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("llm_ranking", "0015_prompt_source_fields"),
        ("websites", "0001_initial"),
        ("prompt_library", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Citation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("url", models.URLField(max_length=2000)),
                ("normalized_url", models.CharField(db_index=True, max_length=2000)),
                ("domain", models.CharField(db_index=True, max_length=300)),
                ("apex_domain", models.CharField(db_index=True, max_length=300)),
                ("source_class", models.CharField(
                    choices=[
                        ("reddit", "Reddit"), ("quora", "Quora"),
                        ("stackoverflow", "Stack Overflow"), ("news", "News"),
                        ("wikipedia", "Wikipedia"), ("blog", "Blog"),
                        ("forum", "Forum"), ("docs", "Documentation"),
                        ("social", "Social"), ("youtube", "YouTube"),
                        ("podcast", "Podcast"), ("gov", "Government"),
                        ("edu", "Education"), ("your_site", "Your Site"),
                        ("competitor_site", "Competitor"), ("other", "Other"),
                    ],
                    db_index=True, default="other", max_length=24,
                )),
                ("extraction_method", models.CharField(
                    choices=[
                        ("native", "Native"), ("grounding", "Grounding"),
                        ("regex", "Regex"), ("llm_assisted", "LLM Assisted"),
                    ],
                    default="regex", max_length=16,
                )),
                ("confidence", models.FloatField(default=1.0)),
                ("position", models.IntegerField(blank=True, null=True)),
                ("title", models.CharField(blank=True, max_length=500)),
                ("snippet", models.TextField(blank=True)),
                ("is_target", models.BooleanField(default=False)),
                ("is_competitor", models.BooleanField(default=False)),
                ("audit", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="extracted_citations",
                    to="llm_ranking.llmrankingaudit",
                )),
                ("result", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="extracted_citations",
                    to="llm_ranking.llmrankingresult",
                )),
            ],
            options={"db_table": "citations_citation"},
        ),
        migrations.AddIndex(
            model_name="citation",
            index=models.Index(fields=["audit", "source_class"], name="citations_c_audit_i_idx"),
        ),
        migrations.AddIndex(
            model_name="citation",
            index=models.Index(fields=["apex_domain", "source_class"], name="citations_c_apex_i_idx"),
        ),
        migrations.AddIndex(
            model_name="citation",
            index=models.Index(fields=["result", "position"], name="citations_c_result_i_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="citation",
            unique_together={("result", "normalized_url")},
        ),
        migrations.CreateModel(
            name="DomainClassification",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("apex_domain", models.CharField(max_length=300, unique=True)),
                ("source_class", models.CharField(
                    choices=[
                        ("reddit", "Reddit"), ("quora", "Quora"),
                        ("stackoverflow", "Stack Overflow"), ("news", "News"),
                        ("wikipedia", "Wikipedia"), ("blog", "Blog"),
                        ("forum", "Forum"), ("docs", "Documentation"),
                        ("social", "Social"), ("youtube", "YouTube"),
                        ("podcast", "Podcast"), ("gov", "Government"),
                        ("edu", "Education"), ("your_site", "Your Site"),
                        ("competitor_site", "Competitor"), ("other", "Other"),
                    ],
                    max_length=24,
                )),
                ("notes", models.TextField(blank=True)),
                ("classified_by", models.CharField(default="rules", max_length=24)),
            ],
            options={"db_table": "citations_domainclassification"},
        ),
        migrations.CreateModel(
            name="SourceInfluenceSnapshot",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=32)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("total_citations", models.IntegerField(default=0)),
                ("breakdown", models.JSONField(default=dict)),
                ("top_domains", models.JSONField(default=list)),
                ("industry", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to="prompt_library.industry",
                )),
                ("website", models.ForeignKey(
                    blank=True, null=True,
                    help_text="If set, this snapshot is per-tenant; if null, global.",
                    on_delete=django.db.models.deletion.CASCADE,
                    to="websites.website",
                )),
            ],
            options={"db_table": "citations_sourceinfluencesnapshot"},
        ),
        migrations.AddIndex(
            model_name="sourceinfluencesnapshot",
            index=models.Index(fields=["provider", "period_end"], name="citations_s_provid_i_idx"),
        ),
        migrations.AddIndex(
            model_name="sourceinfluencesnapshot",
            index=models.Index(fields=["website", "period_end"], name="citations_s_websit_i_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="sourceinfluencesnapshot",
            unique_together={("provider", "industry", "website", "period_start", "period_end")},
        ),
    ]
