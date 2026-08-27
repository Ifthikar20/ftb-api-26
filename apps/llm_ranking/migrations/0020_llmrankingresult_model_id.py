# Hand-written: only the model_id field. makemigrations also wants to
# emit unrelated pre-existing state drift (index renames + created_at
# db_index alters); that belongs to its own change.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("llm_ranking", "0019_alignment_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmrankingresult",
            name="model_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
