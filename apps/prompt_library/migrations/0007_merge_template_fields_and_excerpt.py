"""Merge migration — joins the two leaf nodes that were created on
parallel branches:

    0003_auto_phase2_drift
       │
       ├── 0004_brandprompt → 0005_industry_trend → 0006_prompt_excerpt
       │
       └── 0004_template_fields

Both branches make additive, non-overlapping changes so the merge is
a no-op. After this lands, ``python manage.py migrate prompt_library``
runs cleanly without the "Conflicting migrations detected" error.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("prompt_library", "0004_template_fields"),
        ("prompt_library", "0006_prompt_excerpt"),
    ]

    operations = []
