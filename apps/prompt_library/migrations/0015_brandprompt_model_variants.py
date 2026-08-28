# Hand-written: only the model_variants field. makemigrations also wants
# to emit unrelated pre-existing state drift (index renames + created_at
# db_index alters across several models); that belongs to its own change.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prompt_library", "0014_brandprompt_is_archived"),
    ]

    operations = [
        migrations.AddField(
            model_name="brandprompt",
            name="model_variants",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
