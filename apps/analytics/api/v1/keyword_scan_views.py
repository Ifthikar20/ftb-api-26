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

        # Auto-populate TrackedKeyword from scan results
        auto_tracked = 0
        if result.get("keywords"):
            from apps.analytics.models import TrackedKeyword
            trends = result.get("trends", {})

            for kw_data in result["keywords"][:12]:
                kw_text = kw_data["keyword"]
                trend_info = trends.get(kw_text, {})
                interest = trend_info.get("interest", 0)

                obj, created = TrackedKeyword.objects.get_or_create(
                    website_id=website_id,
                    keyword=kw_text,
                    defaults={
                        "target_url": website.url,
                        "search_volume": interest * 100,  # Scale interest to est. volume
                        "difficulty": min(100, max(0, round(kw_data.get("density", 0) * 25))),
                    },
                )
                if created:
                    auto_tracked += 1
                elif interest > 0:
                    # Update existing with fresh data
                    obj.search_volume = interest * 100
                    obj.save(update_fields=["search_volume"])

        result["auto_tracked"] = auto_tracked
        return Response({"data": result})
