"""Backfill alert identity fields for existing rows.

Step 2 of 3. Assigns every existing SafetyAlert a distinct reference,
mirrors detected_at into the first/last-seen window, maps historical
response_auditor rows onto their detector codes, normalizes their
sentiment_score to the judge's -1..1 scale (the auditor used to write 0.0
and 50.0 on ad-hoc scales), and computes recurrence dedupe keys.
"""
import hashlib
import secrets

from django.db import migrations

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Historical response_auditor rows were keyed by issue alone; the mapping
# to detector codes is 1:1, which is what makes 0011's unique constraint
# on (website, result, detector_code) safe to apply after this backfill.
_DETECTOR_BY_ISSUE = {
    "negative": "BS-SENT-001",
    "sentiment_drop": "BS-SENT-002",
    "harmful": "BS-HARM-001",
    "impersonation": "BS-IMP-001",
}

# negative/harmful rows carried 0.0 meaning "hostile"; sentiment_drop rows
# carried 50.0 meaning "neutral on a 0-100 band". Judge-written rows are
# already on -1..1 and are not touched (their agent_id differs).
_SENTIMENT_BY_ISSUE = {"negative": -0.7, "harmful": -0.7, "sentiment_drop": 0.0}

_FIELDS = [
    "reference", "first_seen_at", "last_seen_at",
    "detector_code", "sentiment_score", "dedupe_key",
]


def _fresh_reference(seen: set) -> str:
    while True:
        ref = "BSA-" + "".join(secrets.choice(_ALPHABET) for _ in range(8))
        if ref not in seen:
            seen.add(ref)
            return ref


def _dedupe_key(detector_code: str, result) -> str:
    # Duplicated from services.security.detectors.compute_dedupe_key so this
    # migration never imports application code that may later change shape.
    if result.source_prompt_id:
        prompt_key = str(result.source_prompt_id)
    else:
        normalized = " ".join((result.prompt or "").split()).lower()
        prompt_key = hashlib.sha256(normalized.encode()).hexdigest()
    raw = f"{detector_code}|{prompt_key}|{result.provider or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def backfill(apps, schema_editor):
    SafetyAlert = apps.get_model("brand_vault", "SafetyAlert")
    seen_refs: set = set()
    batch = []
    rows = SafetyAlert.objects.select_related("result").iterator()
    for row in rows:
        row.reference = _fresh_reference(seen_refs)
        row.first_seen_at = row.detected_at
        row.last_seen_at = row.detected_at
        if row.agent_id == "response_auditor":
            code = _DETECTOR_BY_ISSUE.get(row.issue, "")
            row.detector_code = code
            if row.issue in _SENTIMENT_BY_ISSUE and row.sentiment_score is not None:
                row.sentiment_score = _SENTIMENT_BY_ISSUE[row.issue]
            if code and row.result is not None:
                row.dedupe_key = _dedupe_key(code, row.result)
        batch.append(row)
        if len(batch) >= 500:
            SafetyAlert.objects.bulk_update(batch, _FIELDS)
            batch = []
    if batch:
        SafetyAlert.objects.bulk_update(batch, _FIELDS)


class Migration(migrations.Migration):

    dependencies = [
        ("brand_vault", "0009_alert_taxonomy_fields"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
