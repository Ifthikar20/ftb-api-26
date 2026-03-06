from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.websites.models import Website
from apps.websites.services.website_service import WebsiteService
from apps.websites.services.pixel_service import PixelService
from apps.websites.services.verification_service import VerificationService
from apps.websites.api.v1.serializers import (
    WebsiteSerializer,
    WebsiteCreateSerializer,
    WebsiteUpdateSerializer,
    WebsiteSettingsSerializer,
)
from core.exceptions import ResourceNotFound


class WebsiteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        websites = Website.objects.filter(user=request.user).order_by("-created_at")
        serializer = WebsiteSerializer(websites, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WebsiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        website = WebsiteService.create(user=request.user, **serializer.validated_data)
        return Response(WebsiteSerializer(website).data, status=status.HTTP_201_CREATED)


class WebsiteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_website(self, request, pk):
        return WebsiteService.get_for_user(user=request.user, website_id=pk)

    def get(self, request, pk):
        website = self._get_website(request, pk)
        return Response(WebsiteSerializer(website).data)

    def put(self, request, pk):
        website = self._get_website(request, pk)
        serializer = WebsiteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        website = WebsiteService.update(website=website, user=request.user, **serializer.validated_data)
        return Response(WebsiteSerializer(website).data)

    patch = put

    def delete(self, request, pk):
        website = self._get_website(request, pk)
        WebsiteService.delete(website=website, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PixelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        snippet = PixelService.get_snippet(website=website)
        return Response({"pixel_key": str(website.pixel_key), "snippet": snippet})


class PixelVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        result = VerificationService.verify_pixel(website=website)
        return Response(result)


class PixelRegenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        website = WebsiteService.regenerate_pixel_key(website=website, user=request.user)
        return Response({"pixel_key": str(website.pixel_key)})


class WebsiteSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        serializer = WebsiteSettingsSerializer(website.settings)
        return Response(serializer.data)

    def put(self, request, pk):
        website = WebsiteService.get_for_user(user=request.user, website_id=pk)
        serializer = WebsiteSettingsSerializer(website.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
