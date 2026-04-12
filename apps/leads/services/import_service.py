"""
Lead CSV import service — parse, validate, and upsert leads from a CSV file.
"""
import csv
import io
import logging
import uuid

from django.core.validators import validate_email
from django.db import transaction

from apps.leads.models import Lead
from core.logging.audit_logger import audit_log
from core.utils.constants import LeadStatus

logger = logging.getLogger("apps")

# Expected CSV headers (case-insensitive, will be normalized)
EXPECTED_HEADERS = {"email", "name", "company", "source", "status", "score"}
REQUIRED_HEADERS = {"email"}

VALID_STATUSES = {s.value for s in LeadStatus}


class LeadImportService:
    @staticmethod
    @transaction.atomic
    def import_csv(*, website_id: str, csv_file, user) -> dict:
        """
        Parse a CSV file and create/update leads for the given website.

        Expected columns: email, name, company, source, status, score
        Only 'email' is required per row.

        Returns:
            {"created": int, "updated": int, "skipped": int, "errors": list}
        """
        # Read the file — handle both InMemoryUploadedFile and raw strings
        if hasattr(csv_file, "read"):
            content = csv_file.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8-sig")  # handle BOM
        else:
            content = csv_file

        reader = csv.DictReader(io.StringIO(content))

        # Normalize header names
        if reader.fieldnames is None:
            return {"created": 0, "updated": 0, "skipped": 0, "errors": ["Empty CSV file."]}

        normalized_fields = {f.strip().lower(): f for f in reader.fieldnames}
        missing = REQUIRED_HEADERS - set(normalized_fields.keys())
        if missing:
            return {
                "created": 0, "updated": 0, "skipped": 0,
                "errors": [f"Missing required column(s): {', '.join(missing)}"],
            }

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            # Normalize keys
            normalized_row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

            email = normalized_row.get("email", "").lower()
            if not email:
                skipped += 1
                continue

            # Validate email
            try:
                validate_email(email)
            except Exception:
                errors.append(f"Row {row_num}: Invalid email '{email}'")
                skipped += 1
                continue

            name = normalized_row.get("name", "")
            company = normalized_row.get("company", "")
            source = normalized_row.get("source", "csv_import")
            status = normalized_row.get("status", "").lower()
            score_raw = normalized_row.get("score", "")

            # Validate status
            if status and status not in VALID_STATUSES:
                status = LeadStatus.NEW
            elif not status:
                status = LeadStatus.NEW

            # Parse score
            try:
                score = max(0, min(100, int(score_raw))) if score_raw else 0
            except (ValueError, TypeError):
                score = 0

            # Upsert: check if lead with this email already exists for this website
            existing = Lead.objects.filter(
                website_id=website_id, email__iexact=email
            ).first()

            if existing:
                # Update non-empty fields
                changed = False
                if name and not existing.name:
                    existing.name = name
                    changed = True
                if company and not existing.company:
                    existing.company = company
                    changed = True
                if source and source != "csv_import" and not existing.source:
                    existing.source = source
                    changed = True
                if score > existing.score:
                    existing.score = score
                    changed = True
                if changed:
                    existing.save()
                updated += 1
            else:
                # Create a synthetic visitor for CSV-imported leads
                from apps.analytics.models import Visitor

                visitor = Visitor.objects.create(
                    website_id=website_id,
                    fingerprint_hash=f"csv_import_{uuid.uuid4().hex[:16]}",
                    visit_count=0,
                    lead_score=score,
                )

                Lead.objects.create(
                    visitor=visitor,
                    website_id=website_id,
                    email=email,
                    name=name,
                    company=company,
                    source=source or "csv_import",
                    status=status,
                    score=score,
                )
                created += 1

        audit_log(
            "lead.imported_csv",
            user=user,
            action="import",
            resource_type="lead",
            metadata={
                "website_id": website_id,
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "error_count": len(errors),
            },
        )

        logger.info(
            "CSV import for website %s: created=%d, updated=%d, skipped=%d, errors=%d",
            website_id, created, updated, skipped, len(errors),
        )

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:50],  # Cap at 50 error messages
        }
