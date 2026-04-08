import csv
import io

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import (
    CompetitorDomain,
    CompetitorKeywordRank,
    KeywordAlert,
    KeywordAlertEvent,
    KeywordRankHistory,
    KeywordScanConfig,
    PlatformContent,
    TrackedKeyword,
)
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


# ---------------------------------------------------------------------------
# Content Gap Report Export
# ---------------------------------------------------------------------------

class KeywordComparisonExportView(APIView):
    """Export the keyword comparison (gap analysis) as CSV or an HTML report."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        fmt = request.query_params.get("format", "csv").lower()

        site_keywords = set(
            TrackedKeyword.objects.filter(website_id=website_id).values_list("keyword", flat=True)
        )
        platform_kw_map = {}
        posts = PlatformContent.objects.filter(website_id=website_id).only("platform", "extracted_keywords")
        for post in posts:
            for entry in (post.extracted_keywords or []):
                kw = entry.get("keyword", "")
                if kw:
                    platform_kw_map.setdefault(kw, set()).add(post.platform)

        platform_keywords = set(platform_kw_map.keys())
        rows = []
        for kw in sorted(site_keywords | platform_keywords):
            on_site = kw in site_keywords
            in_posts = kw in platform_keywords
            if on_site and in_posts:
                category = "Overlap"
            elif on_site:
                category = "Gap (add to posts)"
            else:
                category = "Opportunity (add to site)"
            platforms = ", ".join(sorted(platform_kw_map.get(kw, set())))
            rows.append((kw, category, "Yes" if on_site else "No", "Yes" if in_posts else "No", platforms))

        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Keyword", "Category", "On Site", "In Posts", "Platforms"])
            writer.writerows(rows)
            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="keyword-gap-report.csv"'
            return response

        # HTML report (printable)
        rows_html = "".join(
            f"<tr><td>{r[0]}</td><td class='{r[1].split()[0].lower()}'>{r[1]}</td>"
            f"<td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
            for r in rows
        )
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Keyword Gap Report</title>
<style>
  body{{font-family:system-ui,sans-serif;padding:32px;color:#111}}
  h1{{font-size:22px;margin-bottom:4px}}
  p.sub{{color:#666;font-size:13px;margin-bottom:24px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{background:#f4f4f5;text-align:left;padding:8px 10px;border-bottom:2px solid #e4e4e7}}
  td{{padding:7px 10px;border-bottom:1px solid #f0f0f0}}
  tr:hover td{{background:#fafafa}}
  .overlap{{color:#6366f1;font-weight:600}}
  .gap{{color:#d97706;font-weight:600}}
  .opportunity{{color:#16a34a;font-weight:600}}
  @media print{{body{{padding:16px}}}}
</style></head><body>
<h1>Keyword Gap Report</h1>
<p class="sub">Site keywords: {len(site_keywords)} &nbsp;|&nbsp; Platform post keywords: {len(platform_keywords)} &nbsp;|&nbsp; Total rows: {len(rows)}</p>
<table>
  <thead><tr><th>Keyword</th><th>Category</th><th>On Site</th><th>In Posts</th><th>Platforms</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</body></html>"""
        response = HttpResponse(html, content_type="text/html")
        response["Content-Disposition"] = 'attachment; filename="keyword-gap-report.html"'
        return response


# ---------------------------------------------------------------------------
# Keyword Alerts
# ---------------------------------------------------------------------------

class KeywordAlertListView(APIView):
    """List or create keyword position alerts."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        alerts = KeywordAlert.objects.filter(website_id=website_id).select_related("tracked_keyword")
        return Response([self._serialize(a) for a in alerts])

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        threshold = int(request.data.get("threshold", 3))
        direction = request.data.get("direction", KeywordAlert.DIRECTION_ANY)
        method = request.data.get("notification_method", KeywordAlert.METHOD_EMAIL)
        keyword_id = request.data.get("tracked_keyword_id")

        tracked_keyword = None
        if keyword_id:
            try:
                tracked_keyword = TrackedKeyword.objects.get(id=keyword_id, website_id=website_id)
            except TrackedKeyword.DoesNotExist:
                return Response({"error": "Keyword not found"}, status=status.HTTP_404_NOT_FOUND)

        alert = KeywordAlert.objects.create(
            website=website,
            tracked_keyword=tracked_keyword,
            threshold=max(1, threshold),
            direction=direction,
            notification_method=method,
        )
        return Response(self._serialize(alert), status=status.HTTP_201_CREATED)

    @staticmethod
    def _serialize(a):
        return {
            "id": str(a.id),
            "tracked_keyword_id": str(a.tracked_keyword_id) if a.tracked_keyword_id else None,
            "keyword": a.tracked_keyword.keyword if a.tracked_keyword else "All keywords",
            "threshold": a.threshold,
            "direction": a.direction,
            "notification_method": a.notification_method,
            "is_active": a.is_active,
            "last_triggered_at": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
        }


class KeywordAlertDetailView(APIView):
    """Update or delete a keyword alert."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, website_id, alert_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            alert = KeywordAlert.objects.get(id=alert_id, website_id=website_id)
        except KeywordAlert.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        for field in ("threshold", "direction", "notification_method", "is_active"):
            if field in request.data:
                setattr(alert, field, request.data[field])
        alert.save()
        return Response(KeywordAlertListView._serialize(alert))

    def delete(self, request, website_id, alert_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            alert = KeywordAlert.objects.get(id=alert_id, website_id=website_id)
        except KeywordAlert.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        alert.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeywordAlertEventListView(APIView):
    """List recent alert firing events for a website."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        events = KeywordAlertEvent.objects.filter(
            alert__website_id=website_id
        ).select_related("alert").order_by("-triggered_at")[:50]
        return Response([{
            "id": str(e.id),
            "keyword": e.keyword,
            "old_rank": e.old_rank,
            "new_rank": e.new_rank,
            "change": e.change,
            "direction": "improved" if e.change > 0 else "declined",
            "triggered_at": e.triggered_at.isoformat(),
            "alert_threshold": e.alert.threshold,
        } for e in events])


# ---------------------------------------------------------------------------
# Competitor Tracking
# ---------------------------------------------------------------------------

class CompetitorListView(APIView):
    """List or add competitor domains."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        competitors = CompetitorDomain.objects.filter(website_id=website_id)
        return Response([self._serialize(c) for c in competitors])

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        domain = request.data.get("domain", "").strip().lower()
        domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        if not domain:
            return Response({"error": "domain is required"}, status=status.HTTP_400_BAD_REQUEST)
        comp, created = CompetitorDomain.objects.get_or_create(
            website=website,
            domain=domain,
            defaults={"name": request.data.get("name", "")},
        )
        if not created:
            return Response({"error": "Competitor already tracked"}, status=status.HTTP_409_CONFLICT)
        return Response(self._serialize(comp), status=status.HTTP_201_CREATED)

    @staticmethod
    def _serialize(c, with_ranks=False):
        data = {
            "id": str(c.id),
            "domain": c.domain,
            "name": c.name,
            "is_active": c.is_active,
            "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None,
        }
        if with_ranks:
            # latest rank per keyword
            latest = {}
            for r in c.ranks.order_by("keyword", "-checked_at"):
                if r.keyword not in latest:
                    latest[r.keyword] = {"keyword": r.keyword, "rank": r.rank}
            data["ranks"] = list(latest.values())
        return data


class CompetitorDetailView(APIView):
    """Delete a competitor or fetch its latest rankings."""
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, competitor_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            comp = CompetitorDomain.objects.get(id=competitor_id, website_id=website_id)
        except CompetitorDomain.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(CompetitorListView._serialize(comp, with_ranks=True))

    def delete(self, request, website_id, competitor_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            comp = CompetitorDomain.objects.get(id=competitor_id, website_id=website_id)
        except CompetitorDomain.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        comp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompetitorRefreshView(APIView):
    """
    POST — trigger a DataForSEO rank check for this competitor against all
    tracked keywords for the website.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, competitor_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            comp = CompetitorDomain.objects.get(id=competitor_id, website_id=website_id)
        except CompetitorDomain.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        from apps.analytics.tasks import check_competitor_rankings
        check_competitor_rankings.delay(str(comp.id))
        return Response({"queued": True, "competitor": comp.domain})


class CompetitorOverlapView(APIView):
    """
    Side-by-side comparison: our site's rank vs competitors' ranks for
    every tracked keyword.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        keywords = TrackedKeyword.objects.filter(website_id=website_id)
        competitors = CompetitorDomain.objects.filter(website_id=website_id, is_active=True)

        # Build latest rank map per competitor per keyword
        comp_ranks = {}
        for comp in competitors:
            latest = {}
            for r in CompetitorKeywordRank.objects.filter(
                competitor=comp
            ).order_by("keyword", "-checked_at"):
                if r.keyword not in latest:
                    latest[r.keyword] = r.rank
            comp_ranks[str(comp.id)] = {
                "domain": comp.domain,
                "name": comp.name or comp.domain,
                "ranks": latest,
            }

        rows = []
        for kw in keywords:
            row = {
                "keyword": kw.keyword,
                "our_rank": kw.current_rank,
                "competitors": [
                    {
                        "id": cid,
                        "domain": cd["domain"],
                        "name": cd["name"],
                        "rank": cd["ranks"].get(kw.keyword),
                    }
                    for cid, cd in comp_ranks.items()
                ],
            }
            rows.append(row)

        return Response({
            "keywords": rows,
            "competitors": [
                {"id": cid, "domain": cd["domain"], "name": cd["name"]}
                for cid, cd in comp_ranks.items()
            ],
        })
