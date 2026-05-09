from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0009_drop_competitor_models"),
    ]

    operations = [
        migrations.DeleteModel(name="KeywordAlertEvent"),
        migrations.DeleteModel(name="KeywordAlert"),
        migrations.DeleteModel(name="KeywordRankHistory"),
        migrations.DeleteModel(name="TrackedKeyword"),
        migrations.DeleteModel(name="KeywordScanConfig"),
        migrations.DeleteModel(name="PlatformContent"),
        migrations.RunSQL(
            sql=(
                "DROP TABLE IF EXISTS analytics_keywordalertevent CASCADE; "
                "DROP TABLE IF EXISTS analytics_keywordalert CASCADE; "
                "DROP TABLE IF EXISTS analytics_keywordrankhistory CASCADE; "
                "DROP TABLE IF EXISTS analytics_trackedkeyword CASCADE; "
                "DROP TABLE IF EXISTS analytics_keywordscanconfig CASCADE; "
                "DROP TABLE IF EXISTS analytics_platformcontent CASCADE;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
