from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.competitors.models import Competitor
from apps.competitors.services.discovery_service import DiscoveryService
from apps.competitors.services.comparison_service import ComparisonService
from apps.competitors.api.v1.serializers import CompetitorSerializer, CompetitorChangeSerializer
from apps.websites.services.website_service import WebsiteService
from core.exceptions import ResourceNotFound


class CompetitorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        competitors = Competitor.objects.filter(website_id=website_id)
        return Response(CompetitorSerializer(competitors, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        competitor_url = request.data.get("competitor_url", "")
        name = request.data.get("name", "")
        competitor = DiscoveryService.add_competitor(website=website, competitor_url=competitor_url, name=name)
        return Response(CompetitorSerializer(competitor).data, status=status.HTTP_201_CREATED)


class CompetitorDiscoverView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        discovered = DiscoveryService.auto_detect(website=website)
        return Response({"discovered": discovered})


class CompetitorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_competitor(self, website_id, comp_id):
        try:
            return Competitor.objects.get(id=comp_id, website_id=website_id)
        except Competitor.DoesNotExist:
            raise ResourceNotFound("Competitor not found.")

    def get(self, request, website_id, comp_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        competitor = self._get_competitor(website_id, comp_id)
        return Response(CompetitorSerializer(competitor).data)

    def delete(self, request, website_id, comp_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        competitor = self._get_competitor(website_id, comp_id)
        competitor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompetitorCompareView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        data = ComparisonService.get_comparison_matrix(website_id=website_id)
        return Response(data)


class CompetitorChangesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.competitors.models import CompetitorChange
        changes = CompetitorChange.objects.filter(
            competitor__website_id=website_id
        ).order_by("-detected_at")[:50]
        return Response(CompetitorChangeSerializer(changes, many=True).data)
