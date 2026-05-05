from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from apps.leads.api.v1.serializers import (
    LeadNoteSerializer,
    LeadSegmentSerializer,
    LeadSerializer,
    ScoringConfigSerializer,
)
from apps.leads.models import LeadSegment, ScoringConfig
from apps.leads.services.lead_service import LeadService
from core.views import TenantScopedAPIView, TenantScopedListAPIView


class LeadListView(TenantScopedListAPIView):
    def get(self, request, website_id):
        self.get_website(website_id)
        min_score = request.query_params.get("min_score")
        lead_status = request.query_params.get("status")
        leads = LeadService.get_leads(
            website_id=website_id,
            status=lead_status,
            min_score=int(min_score) if min_score else None,
        )
        return self.paginated_response(leads, LeadSerializer)


class HotLeadsView(TenantScopedListAPIView):
    def get(self, request, website_id):
        self.get_website(website_id)
        leads = LeadService.get_leads(website_id=website_id, min_score=70)
        return self.paginated_response(leads, LeadSerializer)


class LeadDetailView(TenantScopedAPIView):
    def get(self, request, website_id, lead_id):
        self.get_website(website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        return Response(LeadSerializer(lead).data)

    def put(self, request, website_id, lead_id):
        self.get_website(website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        new_status = request.data.get("status")
        if new_status:
            lead = LeadService.update_status(lead=lead, status=new_status, user=request.user)
        return Response(LeadSerializer(lead).data)


class LeadNoteView(TenantScopedAPIView):
    def post(self, request, website_id, lead_id):
        self.get_website(website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        content = request.data.get("content", "")
        note = LeadService.add_note(lead=lead, content=content, user=request.user)
        return Response(LeadNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class LeadExportView(TenantScopedAPIView):
    def post(self, request, website_id):
        self.get_website(website_id)
        csv_data = LeadService.export_csv(website_id=website_id)
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=leads-{website_id}.csv"
        return response


class AILeadFinderView(TenantScopedAPIView):
    """AI-powered lead discovery — search LinkedIn & Twitter via natural language."""

    def get(self, request, website_id):
        """Return current lead finder configuration status."""
        self.get_website(website_id)
        from django.conf import settings

        from apps.leads.services.ai_lead_finder import google_search_configured

        return Response({
            "google_search_configured": google_search_configured(),
            "ai_model_configured": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
            "search_engines": ["linkedin", "twitter"],
            "fallback_available": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
        })

    def post(self, request, website_id):
        self.get_website(website_id)
        prompt = request.data.get("prompt", "").strip()
        if not prompt:
            return Response(
                {"error": "A search prompt is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.leads.services.ai_lead_finder import AILeadFinder

        result = AILeadFinder.search(prompt)
        return Response(result)


class ScoringConfigView(TenantScopedAPIView):
    """Get or update per-website lead scoring configuration."""

    def get(self, request, website_id):
        website = self.get_website(website_id)
        config, _ = ScoringConfig.objects.get_or_create(
            website=website, defaults={"threshold": 70, "weights": {}}
        )
        return Response(ScoringConfigSerializer(config).data)

    def put(self, request, website_id):
        website = self.get_website(website_id)
        config, _ = ScoringConfig.objects.get_or_create(
            website=website, defaults={"threshold": 70, "weights": {}}
        )
        serializer = ScoringConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ScoringConfigSerializer(config).data)


class LeadSegmentListView(TenantScopedAPIView):
    """List and create lead segments for a website."""

    def get(self, request, website_id):
        self.get_website(website_id)
        segments = LeadSegment.objects.filter(website_id=website_id).order_by("-created_at")
        return Response(LeadSegmentSerializer(segments, many=True).data)

    def post(self, request, website_id):
        website = self.get_website(website_id)
        serializer = LeadSegmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(website=website, created_by=request.user)
        return Response(LeadSegmentSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)


class LeadSegmentDetailView(TenantScopedAPIView):
    """Update or delete a single lead segment."""

    def _get_segment(self, website_id, segment_id):
        self.get_website(website_id)
        return self.get_tenant_object(
            LeadSegment.objects.all(), id=segment_id, website_id=website_id
        )

    def put(self, request, website_id, segment_id):
        segment = self._get_segment(website_id, segment_id)
        serializer = LeadSegmentSerializer(segment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LeadSegmentSerializer(segment).data)

    def delete(self, request, website_id, segment_id):
        segment = self._get_segment(website_id, segment_id)
        segment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadEmailView(TenantScopedAPIView):
    """Send emails to leads and view email history."""

    def post(self, request, website_id, lead_id):
        """Send an email to a lead."""
        self.get_website(website_id)
        subject = request.data.get("subject", "").strip()
        body = request.data.get("body", "").strip()
        if not subject or not body:
            return Response(
                {"error": "Subject and body are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.leads.services.email_service import LeadEmailService

        try:
            email_record = LeadEmailService.send_email(
                lead_id=lead_id, website_id=website_id, subject=subject, body=body, sent_by=request.user
            )
            return Response({
                "success": True,
                "status": email_record.status,
                "email_id": email_record.id,
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, website_id, lead_id):
        """Get email history for a lead."""
        self.get_website(website_id)
        from apps.leads.services.email_service import LeadEmailService

        emails = LeadEmailService.get_email_history(lead_id=lead_id, website_id=website_id)
        return Response(emails)



# ── Tracked Links ─────────────────────────────────────────────────────────────

class TrackedLinkListView(TenantScopedListAPIView):
    """Create and list tracked links for a website."""

    def get(self, request, website_id):
        self.get_website(website_id)
        from apps.analytics.models import TrackedLink

        links = TrackedLink.objects.filter(website_id=website_id).order_by("-created_at")
        # TrackedLink has no serializer class — paginate manually with the
        # local dict serializer helper.
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(links, request, view=self)
        return paginator.get_paginated_response(_serialize_tracked_links(page))

    def post(self, request, website_id):
        website = self.get_website(website_id)
        destination_url = request.data.get("destination_url", "").strip()
        if not destination_url:
            return Response({"error": "destination_url is required."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.analytics.services.tracking_service import TrackingService

        link = TrackingService.create_link(
            website=website,
            destination_url=destination_url,
            description=request.data.get("description", ""),
        )
        return Response(_serialize_tracked_link(link), status=status.HTTP_201_CREATED)


class TrackedLinkDetailView(TenantScopedAPIView):
    """Retrieve or delete a tracked link."""

    def _get_link(self, website_id, link_id):
        self.get_website(website_id)
        from apps.analytics.models import TrackedLink
        return self.get_tenant_object(
            TrackedLink.objects.all(), id=link_id, website_id=website_id
        )

    def get(self, request, website_id, link_id):
        link = self._get_link(website_id, link_id)
        from apps.analytics.services.tracking_service import TrackingService
        data = _serialize_tracked_link(link)
        data["stats"] = TrackingService.get_click_stats(tracked_link=link)
        return Response(data)

    def delete(self, request, website_id, link_id):
        link = self._get_link(website_id, link_id)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrackedLinkClicksView(TenantScopedListAPIView):
    """List clicks for a tracked link."""

    def get(self, request, website_id, link_id):
        self.get_website(website_id)
        from apps.analytics.models import LinkClick, TrackedLink

        link = self.get_tenant_object(
            TrackedLink.objects.all(), id=link_id, website_id=website_id
        )
        clicks = LinkClick.objects.filter(tracked_link=link).order_by("-clicked_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(clicks, request, view=self)
        return paginator.get_paginated_response([
            {
                "id": c.id,
                "clicked_at": c.clicked_at,
                "converted": c.converted,
                "referrer": c.referrer,
            }
            for c in page
        ])


def _serialize_tracked_link(link) -> dict:
    return {
        "id": str(link.id),
        "tracking_key": link.tracking_key,
        "destination_url": link.destination_url,
        "description": link.description,
        "click_count": link.click_count,
        "conversion_count": link.conversion_count,
        "created_at": link.created_at,
        "short_url": f"/t/{link.tracking_key}/",
    }


def _serialize_tracked_links(links) -> list:
    return [_serialize_tracked_link(link) for link in links]


# ── Connectors ────────────────────────────────────────────────────────────────

class LeadExportXlsxView(TenantScopedAPIView):
    """Export leads as an Excel (.xlsx) file."""

    def post(self, request, website_id):
        self.get_website(website_id)
        xlsx_data = LeadService.export_xlsx(website_id=website_id)
        response = HttpResponse(
            xlsx_data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename=leads-{website_id}.xlsx"
        return response


class LeadExportDriveView(TenantScopedAPIView):
    """Export leads to a Google Sheet via Google Drive."""

    def post(self, request, website_id):
        website = self.get_website(website_id)
        from apps.leads.services.drive_service import DriveService
        from apps.websites.models import Integration

        try:
            integration = Integration.objects.get(
                website=website, type="google_drive", is_active=True
            )
        except Integration.DoesNotExist:
            return Response(
                {"error": "Google Drive is not connected. Connect it under Integrations."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = DriveService.export_leads_to_sheet(
                website_id=str(website_id),
                integration=integration,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result)


# ── Deduplication ─────────────────────────────────────────────────────────────

class LeadDeduplicationView(TenantScopedAPIView):
    """Find and merge duplicate leads within a website."""

    def get(self, request, website_id):
        """Return clusters of duplicate leads (grouped by email)."""
        self.get_website(website_id)
        from apps.leads.services.deduplication_service import DeduplicationService

        clusters = DeduplicationService.find_duplicates(website_id=website_id)
        return Response({
            "clusters": clusters,
            "total_clusters": len(clusters),
        })

    def post(self, request, website_id):
        """Merge duplicates. Body: {primary_lead_id, duplicate_lead_ids} or {auto: true}."""
        self.get_website(website_id)
        from apps.leads.services.deduplication_service import DeduplicationService

        if request.data.get("auto"):
            result = DeduplicationService.auto_dedup(
                website_id=website_id, user=request.user
            )
            return Response(result)

        primary_id = request.data.get("primary_lead_id")
        dup_ids = request.data.get("duplicate_lead_ids", [])
        if not primary_id or not dup_ids:
            return Response(
                {"error": "primary_lead_id and duplicate_lead_ids are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = DeduplicationService.merge(
            primary_lead_id=primary_id,
            duplicate_lead_ids=dup_ids,
            user=request.user,
            website_id=str(website_id),
        )
        return Response(result)


# ── CSV Import ────────────────────────────────────────────────────────────────

class LeadImportView(TenantScopedAPIView):
    """Import leads from a CSV file."""

    def post(self, request, website_id):
        self.get_website(website_id)
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response(
                {"error": "A CSV file is required. Upload as 'file' in multipart/form-data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.leads.services.import_service import LeadImportService

        result = LeadImportService.import_csv(
            website_id=website_id,
            csv_file=csv_file,
            user=request.user,
        )
        return Response(result, status=status.HTTP_201_CREATED)


# ── Activity Timeline ─────────────────────────────────────────────────────────

class LeadTimelineView(TenantScopedAPIView):
    """Unified chronological timeline of all activity for a lead."""

    def get(self, request, website_id, lead_id):
        self.get_website(website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)

        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        from apps.leads.services.timeline_service import TimelineService

        timeline = TimelineService.get_timeline(lead=lead, limit=limit, offset=offset)
        return Response(timeline)
