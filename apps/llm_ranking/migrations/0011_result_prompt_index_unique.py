from django.db import migrations, models


def backfill_prompt_index(apps, schema_editor):
    """
    Existing rows pre-date the `prompt_index` column and all default
    to 0, which collides with the new UniqueConstraint on
    (audit, prompt_index, provider, run_id). Renumber within each
    (audit, provider, run_id) group so prompt_index becomes 0,1,2,...
    ordered by created_at then id.
    """
    with schema_editor.connection.cursor() as cur:
        cur.execute(
            """
            UPDATE llm_ranking_result AS r
            SET prompt_index = sub.idx - 1
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY audit_id, provider, run_id
                           ORDER BY created_at, id
                       ) AS idx
                FROM llm_ranking_result
            ) AS sub
            WHERE r.id = sub.id;
            """
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0010_audit_cost_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingresult",
            name="prompt_index",
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(backfill_prompt_index, noop),
        migrations.AddConstraint(
            model_name="llmrankingresult",
            constraint=models.UniqueConstraint(
                fields=["audit", "prompt_index", "provider", "run_id"],
                name="uq_llm_result_audit_prompt_provider_run",
            ),
        ),
    ]
