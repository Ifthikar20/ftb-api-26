import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("citations", "0005_sourcescanresult_dates_relevance"),
        ("prompt_library", "0013_promptschedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcescan",
            name="seed_urls",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="sourcescan",
            name="source_prompt",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_scans",
                to="prompt_library.prompt",
            ),
        ),
    ]
