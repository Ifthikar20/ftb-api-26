from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Re-sync AITokenUsage.module and AITokenUsage.provider choices with
    what the codebase actually emits. Pure model-state change; the
    underlying CharField columns are unchanged.

    Module choices: drop the obsolete `lead_finder`, `messaging`,
    `seo_keywords`, `analytics` entries (apps removed long ago); list
    the live emitters: `llm_ranking`, `rag`, `onboarding`.

    Provider choices: list every provider we actually call
    (was previously just four).
    """

    dependencies = [
        ("accounts", "0012_drop_leads_keyword_tables"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aitokenusage",
            name="module",
            field=models.CharField(
                choices=[
                    ("llm_ranking", "LLM Ranking"),
                    ("rag", "RAG / Embeddings"),
                    ("onboarding", "Onboarding scan"),
                ],
                db_index=True,
                max_length=20,
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
                    ("meta", "Meta (Llama)"),
                    ("mistral", "Mistral AI"),
                    ("cohere", "Cohere"),
                    ("deepseek", "DeepSeek"),
                    ("xai", "xAI (Grok)"),
                    ("amazon", "Amazon (Nova / Bedrock)"),
                ],
                default="anthropic",
                max_length=20,
            ),
        ),
    ]
