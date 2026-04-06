from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import KeywordRankHistory, KeywordScanConfig, PlatformContent, TrackedKeyword
from apps.websites.services.website_service import WebsiteService


class KeywordListCreateView(APIView):
    """List tracked keywords or add a new one."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        keywords = TrackedKeyword.objects.filter(website_id=website_id).order_by("-created_at")
        data = []
        for kw in keywords:
            rank_change = None
            if kw.current_rank and kw.previous_rank:
                rank_change = kw.previous_rank - kw.current_rank  # positive = improved
            data.append({
                "id": str(kw.id),
                "keyword": kw.keyword,
                "target_url": kw.target_url,
                "current_rank": kw.current_rank,
                "previous_rank": kw.previous_rank,
                "best_rank": kw.best_rank,
                "rank_change": rank_change,
                "search_volume": kw.search_volume,
                "difficulty": kw.difficulty,
                "created_at": kw.created_at.isoformat() if kw.created_at else None,
            })
        return Response(data)

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        keyword_text = request.data.get("keyword", "").strip()
        if not keyword_text:
            return Response({"error": "keyword is required"}, status=status.HTTP_400_BAD_REQUEST)

        kw, created = TrackedKeyword.objects.get_or_create(
            website_id=website_id,
            keyword=keyword_text,
            defaults={
                "target_url": request.data.get("target_url", ""),
                "search_volume": request.data.get("search_volume", 0),
                "difficulty": request.data.get("difficulty", 0),
            },
        )
        if not created:
            return Response({"error": "Keyword already tracked"}, status=status.HTTP_409_CONFLICT)

        return Response({
            "id": str(kw.id),
            "keyword": kw.keyword,
            "target_url": kw.target_url,
            "current_rank": kw.current_rank,
            "search_volume": kw.search_volume,
            "difficulty": kw.difficulty,
        }, status=status.HTTP_201_CREATED)


class KeywordHistoryView(APIView):
    """Get rank history for a specific tracked keyword."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, keyword_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            kw = TrackedKeyword.objects.get(id=keyword_id, website_id=website_id)
        except TrackedKeyword.DoesNotExist:
            return Response({"error": "Keyword not found"}, status=status.HTTP_404_NOT_FOUND)

        history = KeywordRankHistory.objects.filter(tracked_keyword=kw).order_by("date")[:90]
        data = [
            {"date": h.date.isoformat(), "rank": h.rank, "serp_features": h.serp_features}
            for h in history
        ]
        return Response({
            "keyword": kw.keyword,
            "current_rank": kw.current_rank,
            "best_rank": kw.best_rank,
            "history": data,
        })


class TrendingKeywordsView(APIView):
    """Get today's trending keywords from Google Trends."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        region = request.query_params.get("region", "US")
        data = KeywordIntelligenceService.get_trending_keywords(region=region)
        return Response(data)


class KeywordScoresView(APIView):
    """Get AI-powered opportunity scores for all tracked keywords."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        scored = KeywordIntelligenceService.score_keywords_bulk(website_id=website_id)

        explanation = {
            "method": "FetchBot AI Keyword Score™",
            "components": [
                {"name": "Ranking Potential", "weight": "40%", "desc": "Based on current search position and keyword difficulty. Higher score if you're close to page 1."},
                {"name": "Traffic Potential", "weight": "30%", "desc": "Based on monthly search volume. Higher volume = more potential visitors."},
                {"name": "Quick Win Factor", "weight": "20%", "desc": "Keywords ranked #11-20 get the highest score here — they're on the verge of page 1."},
                {"name": "Content Relevance", "weight": "10%", "desc": "How well your page content matches the keyword intent."},
            ],
            "disclaimer": "Scores are AI-estimated based on available data and should be used as directional guidance. Actual results depend on many factors including competition, content quality, backlinks, and search algorithm updates.",
        }

        return Response({"keywords": scored, "explanation": explanation})


class KeywordSuggestionsView(APIView):
    """Get AI-generated keyword suggestions for this website."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        suggestions = KeywordIntelligenceService.suggest_keywords(
            website_url=website.url, industry=website.industry or ""
        )
        return Response(suggestions)


class KeywordInterestView(APIView):
    """Get interest-over-time data for specific keywords."""
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        from apps.analytics.services.keyword_intelligence_service import KeywordIntelligenceService
        keywords = request.data.get("keywords", [])[:5]
        timeframe = request.data.get("timeframe", "now 7-d")
        data = KeywordIntelligenceService.get_keyword_interest(keywords=keywords, timeframe=timeframe)
        return Response(data)


class KeywordScanConfigView(APIView):
    """GET/PUT the DOM scan schedule for a website."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = KeywordScanConfig.objects.get_or_create(website=website)
        return Response(self._serialize(config))

    def put(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        config, _ = KeywordScanConfig.objects.get_or_create(website=website)

        allowed_intervals = [1, 6, 24, 168]
        if "is_auto_scan_enabled" in request.data:
            config.is_auto_scan_enabled = bool(request.data["is_auto_scan_enabled"])
        if "scan_interval_hours" in request.data:
            hours = int(request.data["scan_interval_hours"])
            if hours not in allowed_intervals:
                return Response({"error": f"scan_interval_hours must be one of {allowed_intervals}"}, status=status.HTTP_400_BAD_REQUEST)
            config.scan_interval_hours = hours
        if "scan_depth" in request.data:
            depth = int(request.data["scan_depth"])
            config.scan_depth = max(1, min(20, depth))

        config.save()
        return Response(self._serialize(config))

    @staticmethod
    def _serialize(config):
        return {
            "is_auto_scan_enabled": config.is_auto_scan_enabled,
            "scan_interval_hours": config.scan_interval_hours,
            "scan_depth": config.scan_depth,
            "last_scanned_at": config.last_scanned_at.isoformat() if config.last_scanned_at else None,
            "next_scan_at": config.next_scan_at.isoformat() if config.next_scan_at else None,
            "total_scans": config.total_scans,
        }


class PlatformContentListView(APIView):
    """List platform content posts or add a new one for keyword comparison."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        platform = request.query_params.get("platform")
        qs = PlatformContent.objects.filter(website_id=website_id)
        if platform:
            qs = qs.filter(platform=platform)
        return Response([self._serialize(p) for p in qs[:100]])

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        content_text = request.data.get("content", "").strip()
        if not content_text:
            return Response({"error": "content is required"}, status=status.HTTP_400_BAD_REQUEST)

        platform = request.data.get("platform", PlatformContent.PLATFORM_LINKEDIN)
        valid_platforms = [c[0] for c in PlatformContent.PLATFORM_CHOICES]
        if platform not in valid_platforms:
            return Response({"error": f"platform must be one of {valid_platforms}"}, status=status.HTTP_400_BAD_REQUEST)

        post = PlatformContent.objects.create(
            website=website,
            platform=platform,
            title=request.data.get("title", ""),
            content=content_text,
            url=request.data.get("url", ""),
            platform_post_id=request.data.get("platform_post_id", ""),
        )
        post.extracted_keywords = post.extract_keywords_from_content()
        post.save(update_fields=["extracted_keywords"])
        return Response(self._serialize(post), status=status.HTTP_201_CREATED)

    @staticmethod
    def _serialize(p):
        return {
            "id": str(p.id),
            "platform": p.platform,
            "platform_display": p.get_platform_display(),
            "title": p.title,
            "content": p.content[:300],
            "url": p.url,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "extracted_keywords": p.extracted_keywords,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }


class PlatformContentDetailView(APIView):
    """Delete a platform content post."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, website_id, post_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            post = PlatformContent.objects.get(id=post_id, website_id=website_id)
        except PlatformContent.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeywordComparisonView(APIView):
    """
    Compare website DOM keywords against platform content keywords.
    Returns overlap, gaps (on site but not in posts), and opportunities
    (trending/in posts but not on site).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)

        # Collect tracked website keywords
        site_keywords = set(
            TrackedKeyword.objects.filter(website_id=website_id).values_list("keyword", flat=True)
        )

        # Collect keywords extracted from platform posts
        platform_kw_map = {}  # keyword -> list of platforms
        posts = PlatformContent.objects.filter(website_id=website_id).only("platform", "extracted_keywords")
        for post in posts:
            for entry in (post.extracted_keywords or []):
                kw = entry.get("keyword", "")
                if kw:
                    platform_kw_map.setdefault(kw, set()).add(post.platform)

        platform_keywords = set(platform_kw_map.keys())

        overlap = sorted(site_keywords & platform_keywords)
        gaps = sorted(site_keywords - platform_keywords)          # on site, not in posts
        opportunities = sorted(platform_keywords - site_keywords) # in posts, not on site

        return Response({
            "site_keyword_count": len(site_keywords),
            "platform_keyword_count": len(platform_keywords),
            "overlap": overlap[:50],
            "gaps": gaps[:50],
            "opportunities": [
                {"keyword": kw, "platforms": sorted(platform_kw_map[kw])}
                for kw in opportunities[:50]
            ],
        })

