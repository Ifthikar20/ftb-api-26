# Per-website archive flag for saved prompts (security fix: archiving no
# longer flips the shared catalog Prompt.is_active across tenants).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prompt_library", "0013_promptschedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="brandprompt",
            name="is_archived",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
