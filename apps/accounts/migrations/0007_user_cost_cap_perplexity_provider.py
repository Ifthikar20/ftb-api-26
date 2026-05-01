from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_alter_organization_plan_alter_user_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="monthly_ai_cost_cap_usd",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Per-user monthly AI spend cap in USD. 0 disables the cap.",
                max_digits=10,
            ),
        ),
        migrations.AlterField(
            model_name="aitokenusage",
            name="provider",
            field=models.CharField(
                choices=[
                    ("anthropic", "Anthropic (Claude)"),
                    ("openai", "OpenAI (GPT)"),
                    ("google", "Google (Gemini)"),
                    ("perplexity", "Perplexity"),
                ],
                default="anthropic",
                max_length=20,
            ),
        ),
    ]
