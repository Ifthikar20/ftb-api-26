# Per-prompt model selection lets one crawl query several variants of the
# same provider inside a single (synthetic) audit, which collides with the
# old (audit, prompt_index, provider, run_id) key. model_id joins the key;
# audit-pipeline rows all carry model_id="" so their semantics are
# unchanged.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0020_llmrankingresult_model_id"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="llmrankingresult",
            name="uq_llm_result_audit_prompt_provider_run",
        ),
        migrations.AddConstraint(
            model_name="llmrankingresult",
            constraint=models.UniqueConstraint(
                fields=["audit", "prompt_index", "provider", "model_id", "run_id"],
                name="uq_llm_result_audit_prompt_provider_run",
            ),
        ),
    ]
