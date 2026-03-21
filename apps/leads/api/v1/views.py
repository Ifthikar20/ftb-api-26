from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.leads.models import LeadSegment, ScoringConfig
from apps.leads.services.lead_service import LeadService
from apps.leads.api.v1.serializers import (
    LeadSerializer,
    LeadNoteSerializer,
    LeadSegmentSerializer,
    ScoringConfigSerializer,
)
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination
from core.exceptions import ResourceNotFound


class LeadListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        min_score = request.query_params.get("min_score")
        lead_status = request.query_params.get("status")
        leads = LeadService.get_leads(
            website_id=website_id,
            status=lead_status,
            min_score=int(min_score) if min_score else None,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(leads, request)
        serializer = LeadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class HotLeadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        leads = LeadService.get_leads(website_id=website_id, min_score=70)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(leads, request)
        serializer = LeadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class LeadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, lead_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        return Response(LeadSerializer(lead).data)

    def put(self, request, website_id, lead_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        new_status = request.data.get("status")
        if new_status:
            lead = LeadService.update_status(lead=lead, status=new_status, user=request.user)
        return Response(LeadSerializer(lead).data)


class LeadNoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, lead_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        lead = LeadService.get_lead(website_id=website_id, lead_id=lead_id)
        content = request.data.get("content", "")
        note = LeadService.add_note(lead=lead, content=content, user=request.user)
        return Response(LeadNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class LeadExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        csv_data = LeadService.export_csv(website_id=website_id)
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=leads-{website_id}.csv"
        return response


class AILeadFinderView(APIView):
    """AI-powered lead discovery — search LinkedIn & Twitter via natural language."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        prompt = request.data.get("prompt", "").strip()
        if not prompt:
            return Response(
                {"error": "A search prompt is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.leads.services.ai_lead_finder import AILeadFinder

        result = AILeadFinder.search(prompt)
        return Response(result)


class LeadEmailView(APIView):
    """Send emails to leads and view email history."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, lead_id):
        """Send an email to a lead."""
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
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
                lead_id=lead_id, subject=subject, body=body, sent_by=request.user
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
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.leads.services.email_service import LeadEmailService

        emails = LeadEmailService.get_email_history(lead_id=lead_id)
        return Response(emails)
