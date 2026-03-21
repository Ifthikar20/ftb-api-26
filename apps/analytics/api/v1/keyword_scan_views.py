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
    POST — trigger a new keyword scan + DataForSEO enrichment
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
        import logging
        from urllib.parse import urlparse
        from django.core.cache import cache
        cache_key = f"seo_scan_{hashlib.md5(website.url.encode()).hexdigest()}"
        cache.delete(cache_key)

        logger = logging.getLogger("apps")

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
                        "search_volume": interest * 100,
                        "difficulty": min(100, max(0, round(kw_data.get("density", 0) * 25))),
                    },
                )
                if created:
                    auto_tracked += 1

        result["auto_tracked"] = auto_tracked

        # DataForSEO enrichment — real rankings, volume, difficulty
        try:
            from apps.analytics.services.dataforseo_service import DataForSEOService
            if DataForSEOService.is_configured():
                domain = urlparse(website.url).netloc.replace("www.", "")
                kw_list = [k["keyword"] for k in result.get("keywords", [])[:12]]

                enriched = DataForSEOService.enrich_keywords(kw_list, domain)
                result["dataforseo"] = enriched
                result["dataforseo_configured"] = True

                # Update TrackedKeyword records with real data
                if enriched:
                    from apps.analytics.models import TrackedKeyword
                    for e in enriched:
                        if e.get("enriched"):
                            try:
                                tk = TrackedKeyword.objects.filter(
                                    website_id=website_id,
                                    keyword=e["keyword"]
                                ).first()
                                if tk:
                                    changed = []
                                    if e.get("volume"):
                                        tk.search_volume = e["volume"]
                                        changed.append("search_volume")
                                    if e.get("difficulty"):
                                        tk.difficulty = e["difficulty"]
                                        changed.append("difficulty")
                                    if e.get("position"):
                                        tk.current_rank = e["position"]
                                        if not tk.best_rank or e["position"] < tk.best_rank:
                                            tk.best_rank = e["position"]
                                            changed.append("best_rank")
                                        changed.append("current_rank")
                                    if changed:
                                        tk.save(update_fields=changed)
                            except Exception as ex:
                                logger.warning(f"DataForSEO update error for {e['keyword']}: {ex}")
            else:
                result["dataforseo_configured"] = False
        except Exception as e:
            logger.warning(f"DataForSEO enrichment failed: {e}")
            result["dataforseo_configured"] = False

        return Response({"data": result})
