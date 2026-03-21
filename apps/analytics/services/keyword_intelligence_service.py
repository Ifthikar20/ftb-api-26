"""
Keyword Intelligence Service — Google Trends integration + AI keyword scoring.
Uses pytrends for trending data and rule-based AI for keyword opportunity scoring.
"""
import logging
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse

from django.db.models import Count, Avg
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger("apps")


class KeywordIntelligenceService:
    """Provides trending keywords, AI scores, and suggestions."""

    # ── Google Trends (via pytrends) ──

    @staticmethod
    def get_trending_keywords(*, region: str = "US", count: int = 20) -> dict:
        """
        Fetch today's trending searches from Google Trends.
        Cached for 30 minutes to avoid rate limiting.
        """
        cache_key = f"gtrends_trending_{region}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
            trending = pytrends.trending_searches(pn=region.lower())
            results = [str(kw) for kw in trending[0].tolist()[:count]]

            data = {
                "keywords": results,
                "region": region,
                "updated_at": timezone.now().isoformat(),
                "source": "Google Trends",
            }
            cache.set(cache_key, data, 1800)  # Cache 30 min
            return data

        except ImportError:
            logger.warning("pytrends not installed — using fallback trending keywords")
            return KeywordIntelligenceService._fallback_trending()
        except Exception as e:
            logger.warning(f"Google Trends fetch failed: {e}")
            return KeywordIntelligenceService._fallback_trending()

    @staticmethod
    def get_keyword_interest(*, keywords: list, timeframe: str = "now 7-d") -> dict:
        """
        Get interest-over-time data for specific keywords from Google Trends.
        Returns relative interest (0-100) for each keyword.
        """
        if not keywords:
            return {"keywords": [], "data": []}

        cache_key = f"gtrends_interest_{hashlib.md5('|'.join(keywords).encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
            pytrends.build_payload(keywords[:5], timeframe=timeframe, geo="US")
            interest = pytrends.interest_over_time()

            if interest.empty:
                return {"keywords": keywords[:5], "data": [], "timeframe": timeframe}

            data_points = []
            for _, row in interest.iterrows():
                point = {"date": str(row.name.date())}
                for kw in keywords[:5]:
                    if kw in row:
                        point[kw] = int(row[kw])
                data_points.append(point)

            result = {
                "keywords": keywords[:5],
                "data": data_points,
                "timeframe": timeframe,
            }
            cache.set(cache_key, result, 3600)
            return result

        except ImportError:
            return {"keywords": keywords[:5], "data": [], "note": "pytrends not installed"}
        except Exception as e:
            logger.warning(f"Interest fetch failed: {e}")
            return {"keywords": keywords[:5], "data": [], "error": str(e)}

    @staticmethod
    def get_related_keywords(*, keyword: str) -> dict:
        """Get related queries and topics for a keyword from Google Trends."""
        cache_key = f"gtrends_related_{hashlib.md5(keyword.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
            pytrends.build_payload([keyword], timeframe="today 3-m", geo="US")

            related_queries = pytrends.related_queries()
            related_topics = pytrends.related_topics()

            rising = []
            top = []

            if keyword in related_queries:
                q = related_queries[keyword]
                if q.get("rising") is not None and not q["rising"].empty:
                    for _, row in q["rising"].head(10).iterrows():
                        rising.append({
                            "keyword": str(row.get("query", "")),
                            "value": int(row.get("value", 0)),
                        })
                if q.get("top") is not None and not q["top"].empty:
                    for _, row in q["top"].head(10).iterrows():
                        top.append({
                            "keyword": str(row.get("query", "")),
                            "value": int(row.get("value", 0)),
                        })

            result = {
                "keyword": keyword,
                "rising": rising,
                "top": top,
            }
            cache.set(cache_key, result, 3600)
            return result

        except ImportError:
            return {"keyword": keyword, "rising": [], "top": [], "note": "pytrends not installed"}
        except Exception as e:
            logger.warning(f"Related keywords fetch failed: {e}")
            return {"keyword": keyword, "rising": [], "top": [], "error": str(e)}

    # ── AI Keyword Scoring ──

    @staticmethod
    def score_keyword(*, keyword: str, current_rank: int = None,
                      search_volume: int = 0, difficulty: int = 0,
                      page_content_relevance: float = None) -> dict:
        """
        Generate an AI-powered keyword opportunity score (0-100).

        Score components:
        - Ranking potential (40%): Based on current rank and difficulty
        - Traffic potential (30%): Based on search volume
        - Quick-win factor (20%): Keywords close to page 1 are high-value
        - Content relevance (10%): If page content matches the keyword

        Returns score, breakdown, and actionable recommendation.
        """
        # Ranking Potential (0-40)
        ranking_score = 0
        if current_rank:
            if current_rank <= 3:
                ranking_score = 38  # Already dominant
            elif current_rank <= 10:
                ranking_score = 35  # Page 1
            elif current_rank <= 20:
                ranking_score = 30  # Striking distance
            elif current_rank <= 30:
                ranking_score = 22
            elif current_rank <= 50:
                ranking_score = 15
            else:
                ranking_score = 8
        else:
            ranking_score = 5  # Not ranking yet

        # Adjust for difficulty
        if difficulty > 0:
            diff_multiplier = max(0.4, 1 - (difficulty / 120))
            ranking_score = round(ranking_score * diff_multiplier)

        # Traffic Potential (0-30)
        traffic_score = 0
        if search_volume >= 10000:
            traffic_score = 30
        elif search_volume >= 5000:
            traffic_score = 26
        elif search_volume >= 1000:
            traffic_score = 22
        elif search_volume >= 500:
            traffic_score = 18
        elif search_volume >= 100:
            traffic_score = 12
        elif search_volume > 0:
            traffic_score = 6
        else:
            traffic_score = 2

        # Quick-Win Factor (0-20)
        quick_win = 0
        if current_rank and 11 <= current_rank <= 20:
            quick_win = 20  # Striking distance — highest priority!
        elif current_rank and 4 <= current_rank <= 10:
            quick_win = 15  # Almost at #1-3
        elif current_rank and 21 <= current_rank <= 30:
            quick_win = 10
        elif current_rank and current_rank <= 3:
            quick_win = 5  # Already there, defend it

        # Content Relevance (0-10)
        relevance_score = 5  # Default middle score
        if page_content_relevance is not None:
            relevance_score = round(page_content_relevance * 10)

        total = min(100, ranking_score + traffic_score + quick_win + relevance_score)

        # Generate recommendation
        rec = KeywordIntelligenceService._get_recommendation(
            total, current_rank, difficulty, search_volume
        )

        return {
            "score": total,
            "grade": KeywordIntelligenceService._score_to_grade(total),
            "breakdown": {
                "ranking_potential": {"score": ranking_score, "max": 40, "label": "Ranking Potential"},
                "traffic_potential": {"score": traffic_score, "max": 30, "label": "Traffic Potential"},
                "quick_win": {"score": quick_win, "max": 20, "label": "Quick Win Factor"},
                "relevance": {"score": relevance_score, "max": 10, "label": "Content Relevance"},
            },
            "recommendation": rec,
            "calculation_method": "FetchBot AI Keyword Score™ combines ranking position, search volume, keyword difficulty, quick-win proximity to page 1, and content relevance to estimate the opportunity value of targeting this keyword.",
        }

    @staticmethod
    def _score_to_grade(score):
        if score >= 80:
            return {"label": "Excellent", "color": "#22c55e"}
        if score >= 60:
            return {"label": "Good", "color": "#3b82f6"}
        if score >= 40:
            return {"label": "Fair", "color": "#eab308"}
        if score >= 20:
            return {"label": "Low", "color": "#f97316"}
        return {"label": "Poor", "color": "#ef4444"}

    @staticmethod
    def _get_recommendation(score, rank, difficulty, volume):
        if rank and 11 <= rank <= 20 and difficulty < 50:
            return "🎯 Quick Win — This keyword is on page 2. Small SEO improvements could push it to page 1 for significant traffic gains."
        if rank and rank <= 3:
            return "🛡️ Defend Position — You're in the top 3. Focus on maintaining freshness and building more backlinks."
        if rank and rank <= 10 and volume >= 1000:
            return "📈 Optimize — Already on page 1 with good volume. Optimize title, meta description, and content to climb to top 3."
        if not rank and difficulty < 30 and volume >= 500:
            return "🌱 New Opportunity — Not yet ranking for this easy keyword with decent volume. Create targeted content."
        if difficulty >= 70:
            return "⚔️ Competitive — High difficulty keyword. Consider long-tail variations or building topical authority first."
        if volume < 100:
            return "🔬 Niche — Low volume but may have high conversion intent. Good for targeted landing pages."
        return "📊 Monitor — Track this keyword and look for content opportunities to improve your position."

    @staticmethod
    def score_keywords_bulk(*, website_id: str) -> list:
        """Score all tracked keywords for a website."""
        from apps.analytics.models import TrackedKeyword
        keywords = TrackedKeyword.objects.filter(website_id=website_id)
        scored = []
        for kw in keywords:
            score_data = KeywordIntelligenceService.score_keyword(
                keyword=kw.keyword,
                current_rank=kw.current_rank,
                search_volume=kw.search_volume,
                difficulty=kw.difficulty,
            )
            scored.append({
                "id": str(kw.id),
                "keyword": kw.keyword,
                "current_rank": kw.current_rank,
                "search_volume": kw.search_volume,
                "difficulty": kw.difficulty,
                "ai_score": score_data["score"],
                "grade": score_data["grade"],
                "recommendation": score_data["recommendation"],
            })
        scored.sort(key=lambda x: x["ai_score"], reverse=True)
        return scored

    @staticmethod
    def suggest_keywords(*, website_url: str, industry: str = "") -> list:
        """
        Suggest keywords based on the website URL and industry.
        Uses Google Trends related searches if available.
        """
        try:
            domain = urlparse(website_url).hostname or website_url
        except Exception:
            domain = website_url

        # Try to get related keywords from the domain/industry
        seed = industry if industry else domain.replace("www.", "").split(".")[0]
        related = KeywordIntelligenceService.get_related_keywords(keyword=seed)

        suggestions = []
        for r in related.get("rising", [])[:8]:
            suggestions.append({
                "keyword": r["keyword"],
                "source": "Rising on Google Trends",
                "trend": "rising",
                "value": r.get("value", 0),
            })
        for t in related.get("top", [])[:8]:
            suggestions.append({
                "keyword": t["keyword"],
                "source": "Top related search",
                "trend": "stable",
                "value": t.get("value", 0),
            })

        return suggestions[:15]

    # ── Fallback ──

    @staticmethod
    def _fallback_trending():
        """Fallback trending keywords when Google Trends is unavailable."""
        return {
            "keywords": [],
            "region": "US",
            "updated_at": timezone.now().isoformat(),
            "source": "unavailable",
            "note": "Install pytrends (`pip install pytrends`) to get real-time Google Trends data.",
        }
