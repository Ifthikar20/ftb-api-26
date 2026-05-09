"""Add nullable FK from LLMRankingResult to prompt_library.Prompt.

Lets the effectiveness scorer aggregate audit signals back to the
template that produced them without text-matching against filled
prompts (variables differ per website).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0015_prompt_source_fields"),
        ("prompt_library", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingresult",
            name="source_prompt",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ranking_results",
                to="prompt_library.prompt",
            ),
        ),
    ]
