from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.leads.services.lead_service import LeadService
from apps.leads.api.v1.serializers import LeadSerializer, LeadNoteSerializer
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination


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
        serializer = LeadSerializer(leads, many=True)
        return Response(serializer.data)


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
