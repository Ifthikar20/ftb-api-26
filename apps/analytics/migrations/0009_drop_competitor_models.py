from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0008_drop_campaign_fks"),
    ]

    operations = [
        migrations.DeleteModel(name="CompetitorKeywordRank"),
        migrations.DeleteModel(name="CompetitorDomain"),
        migrations.RunSQL(
            sql=(
                "DROP TABLE IF EXISTS analytics_competitorkeywordrank CASCADE; "
                "DROP TABLE IF EXISTS analytics_competitordomain CASCADE;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
