"""Add a non-sequential public_id to LLMRankingResult.

Done in three steps so existing rows each get a distinct UUID before the
unique constraint is applied (a single default would collide).
"""
import uuid

from django.db import migrations, models


def backfill_public_id(apps, schema_editor):
    Result = apps.get_model("llm_ranking", "LLMRankingResult")
    # Assign a fresh UUID to every existing row, in batches.
    to_update = []
    for row in Result.objects.all().only("id").iterator():
        row.public_id = uuid.uuid4()
        to_update.append(row)
        if len(to_update) >= 1000:
            Result.objects.bulk_update(to_update, ["public_id"])
            to_update = []
    if to_update:
        Result.objects.bulk_update(to_update, ["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0017_modeltestrun"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingresult",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(backfill_public_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="llmrankingresult",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, unique=True, db_index=True,
            ),
        ),
    ]
