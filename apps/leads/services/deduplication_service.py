"""
Lead deduplication service — find and merge duplicate leads.

Duplicates are identified by normalized email within a website.
Merging re-parents notes, emails, and campaign receipts to the
primary (highest-scoring) lead and soft-deletes the rest.
"""
import logging
from collections import defaultdict

from django.db import transaction
from django.db.models import Count, Max

from apps.leads.models import CampaignRecipient, Lead, LeadEmail, LeadNote
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")


class DeduplicationService:
    @staticmethod
    def find_duplicates(*, website_id: str) -> list[dict]:
        """
        Find clusters of leads that share the same email.
        Returns a list of duplicate groups, each with the leads involved.
        """
        # Find emails that appear more than once (ignoring blanks)
        dup_emails = (
            Lead.objects.filter(website_id=website_id)
            .exclude(email="")
            .values("email")
            .annotate(count=Count("id"), max_score=Max("score"))
            .filter(count__gt=1)
            .order_by("-max_score")
        )

        clusters = []
        for entry in dup_emails:
            leads = Lead.objects.filter(
                website_id=website_id, email=entry["email"]
            ).order_by("-score", "-created_at")

            clusters.append({
                "email": entry["email"],
                "count": entry["count"],
                "primary": _lead_to_dict(leads.first()),
                "duplicates": [_lead_to_dict(l) for l in leads[1:]],
            })

        return clusters

    @staticmethod
    @transaction.atomic
    def merge(*, primary_lead_id: str, duplicate_lead_ids: list[str], user=None) -> dict:
        """
        Merge duplicate leads into a single primary lead.

        - Re-parents notes, emails, and campaign receipts to primary
        - Fills empty fields on primary from duplicates
        - Soft-deletes the duplicate leads
        """
        primary = Lead.objects.select_for_update().get(id=primary_lead_id)
        duplicates = Lead.objects.select_for_update().filter(id__in=duplicate_lead_ids)

        merged_count = 0

        for dup in duplicates:
            if dup.id == primary.id:
                continue

            # Re-parent related objects
            LeadNote.objects.filter(lead=dup).update(lead=primary)
            LeadEmail.objects.filter(lead=dup).update(lead=primary)

            # Campaign recipients — skip if primary already has one for the same campaign
            for recipient in CampaignRecipient.objects.filter(lead=dup):
                if not CampaignRecipient.objects.filter(
                    campaign=recipient.campaign, lead=primary
                ).exists():
                    recipient.lead = primary
                    recipient.save(update_fields=["lead"])
                else:
                    recipient.delete()

            # Fill empty fields from duplicate
            for field in ("name", "company", "source", "email"):
                if not getattr(primary, field) and getattr(dup, field):
                    setattr(primary, field, getattr(dup, field))

            # Keep the higher score
            if dup.score > primary.score:
                primary.score = dup.score

            # Soft-delete the duplicate
            dup.delete()  # SoftDeleteMixin.delete() sets is_deleted=True
            merged_count += 1

        primary.save()

        audit_log(
            "lead.merged",
            user=user,
            action="merge",
            resource_type="lead",
            resource_id=str(primary.id),
            metadata={
                "merged_count": merged_count,
                "duplicate_ids": duplicate_lead_ids,
                "website_id": str(primary.website_id),
            },
        )

        logger.info(
            "Merged %d duplicates into lead %s", merged_count, primary.id
        )

        return {
            "primary_id": str(primary.id),
            "merged_count": merged_count,
        }

    @classmethod
    def auto_dedup(cls, *, website_id: str, user=None) -> dict:
        """
        Automatically find and merge all duplicate clusters for a website.
        Uses exact email match.
        """
        clusters = cls.find_duplicates(website_id=website_id)
        total_merged = 0

        for cluster in clusters:
            primary_id = cluster["primary"]["id"]
            dup_ids = [d["id"] for d in cluster["duplicates"]]
            result = cls.merge(
                primary_lead_id=primary_id,
                duplicate_lead_ids=dup_ids,
                user=user,
            )
            total_merged += result["merged_count"]

        return {
            "clusters_processed": len(clusters),
            "total_merged": total_merged,
        }


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "id": str(lead.id),
        "email": lead.email,
        "name": lead.name,
        "company": lead.company,
        "score": lead.score,
        "status": lead.status,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }
