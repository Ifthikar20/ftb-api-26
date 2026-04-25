from django.db import migrations


class Migration(migrations.Migration):
    """Drop the vestigial voice_call_queued boolean from SocialLead.

    Removes the column so no stale references remain in the schema.
    """

    dependencies = [
        ("social_leads", "0002_remove_socialleadsource_unique_website_platform_form_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sociallead",
            name="voice_call_queued",
        ),
    ]
