import csv
import io
import logging

from core.logging.audit_logger import audit_log
from core.exceptions import ResourceNotFound
from apps.leads.models import Lead, LeadNote

logger = logging.getLogger("apps")


class LeadService:
    @staticmethod
    def get_leads(*, website_id: str, status: str = None, min_score: int = None):
        qs = Lead.objects.filter(website_id=website_id).order_by("-score")
        if status:
            qs = qs.filter(status=status)
        if min_score is not None:
            qs = qs.filter(score__gte=min_score)
        return qs

    @staticmethod
    def get_lead(*, website_id: str, lead_id: str) -> Lead:
        try:
            return Lead.objects.get(id=lead_id, website_id=website_id)
        except Lead.DoesNotExist:
            raise ResourceNotFound("Lead not found.")

    @staticmethod
    def update_status(*, lead: Lead, status: str, user) -> Lead:
        lead.status = status
        lead.save(update_fields=["status", "updated_at"])
        audit_log("lead.status_updated", user=user, metadata={"lead_id": str(lead.id), "status": status})
        return lead

    @staticmethod
    def add_note(*, lead: Lead, content: str, user) -> LeadNote:
        return LeadNote.objects.create(lead=lead, author=user, content=content)

    @staticmethod
    def export_csv(*, website_id: str) -> str:
        leads = Lead.objects.filter(website_id=website_id).select_related("visitor")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Score", "Status", "Email", "Company", "Source", "Created At"])
        for lead in leads:
            writer.writerow([
                str(lead.id), lead.score, lead.status, lead.email,
                lead.company, lead.source, lead.created_at.isoformat(),
            ])
        return output.getvalue()
