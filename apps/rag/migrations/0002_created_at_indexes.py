from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add the ``db_index=True`` that ``TimestampMixin.created_at`` declares
    but the hand-written 0001_initial omitted. Without this the model
    and the migration state disagree and Django emits a "models in
    app(s): 'rag' have changes" warning on every ``migrate``.
    """

    dependencies = [
        ("rag", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knowledgesource",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="knowledgechunk",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
