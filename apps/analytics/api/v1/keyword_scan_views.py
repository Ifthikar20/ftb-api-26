"""
Keyword Scan API — trigger an SEO keyword scan and retrieve results.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.analytics.services.seo_keyword_scanner import SEOKeywordScanner
from apps.websites.models import Website


class KeywordScanView(APIView):
    """
    GET  — return latest cached scan results
    POST — trigger a new keyword scan
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id, user=request.user)
        except Website.DoesNotExist:
            return Response({"error": "Website not found"}, status=404)

        result = SEOKeywordScanner.scan(
            website_url=website.url,
            website_id=str(website.id),
        )
        return Response({"data": result})

    def post(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id, user=request.user)
        except Website.DoesNotExist:
            return Response({"error": "Website not found"}, status=404)

        # Clear cache to force fresh scan
        import hashlib
        from django.core.cache import cache
        cache_key = f"seo_scan_{hashlib.md5(website.url.encode()).hexdigest()}"
        cache.delete(cache_key)

        result = SEOKeywordScanner.scan(
            website_url=website.url,
            website_id=str(website.id),
        )
        return Response({"data": result})
