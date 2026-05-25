from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prompt_library", "0010_promptfanout_promptcrawlrun"),
    ]

    operations = [
        migrations.AddField(
            model_name="brandprompt",
            name="tags",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="brandprompt",
            name="location",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
    ]
