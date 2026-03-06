from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.analytics.models import TrackedKeyword, KeywordRankHistory
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
