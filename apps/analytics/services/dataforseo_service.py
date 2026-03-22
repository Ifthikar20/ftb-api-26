"""
DataForSEO API Service — Real keyword rankings, search volume, difficulty, and SERP features.
Uses DataForSEO REST API v3 with HTTP Basic Auth.
"""
import base64
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps")

DATAFORSEO_BASE = "https://api.dataforseo.com/v3"


class DataForSEOService:
    """Integrate with DataForSEO for real SEO data."""

    @staticmethod
    def _auth_headers():
        login = getattr(settings, "DATAFORSEO_LOGIN", "")
        password = getattr(settings, "DATAFORSEO_PASSWORD", "")
        if not login or not password:
            return None
        creds = base64.b64encode(f"{login}:{password}".encode()).decode()
        return {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def is_configured():
        return bool(getattr(settings, "DATAFORSEO_LOGIN", "")) and bool(getattr(settings, "DATAFORSEO_PASSWORD", ""))

    @staticmethod
    def get_serp_rankings(keyword: str, domain: str, location_code: int = 2840, language_code: str = "en") -> dict:
        """
        Get live Google SERP for a keyword and find where domain ranks.
        Returns: position, url, title, snippet, serp_features present.
        """
        headers = DataForSEOService._auth_headers()
        if not headers:
            return {"error": "DataForSEO not configured", "configured": False}

        cache_key = f"dfs_serp_{keyword}_{domain}_{location_code}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            payload = [{
                "keyword": keyword,
                "location_code": location_code,
                "language_code": language_code,
                "depth": 100,
                "device": "desktop",
            }]
            resp = requests.post(
                f"{DATAFORSEO_BASE}/serp/google/organic/live/regular",
                headers=headers,
                json=payload,
                timeout=30,
            )
            data = resp.json()

            if data.get("status_code") != 20000:
                return {"error": data.get("status_message", "API error")}

            result = {
                "keyword": keyword,
                "domain": domain,
                "position": None,
                "url": None,
                "title": None,
                "snippet": None,
                "serp_features": [],
                "total_results": 0,
                "top_competitors": [],
            }

            tasks = data.get("tasks", [])
            if tasks and tasks[0].get("result"):
                task_result = tasks[0]["result"][0]
                result["total_results"] = task_result.get("se_results_count", 0)

                items = task_result.get("items", [])
                serp_types = set()
                domain_lower = domain.lower()

                for item in items:
                    item_type = item.get("type", "")
                    serp_types.add(item_type)

                    if item_type == "organic":
                        item_domain = (item.get("domain") or "").lower()
                        rank = item.get("rank_group")

                        # Check if this is our domain
                        if domain_lower in item_domain or item_domain in domain_lower:
                            result["position"] = rank
                            result["url"] = item.get("url")
                            result["title"] = item.get("title")
                            result["snippet"] = item.get("description")

                        # Top 5 competitors
                        if rank and rank <= 5:
                            result["top_competitors"].append({
                                "position": rank,
                                "domain": item.get("domain"),
                                "url": item.get("url"),
                                "title": item.get("title"),
                            })

                result["serp_features"] = list(serp_types)

            cache.set(cache_key, result, 3600)  # Cache 1 hr
            return result

        except Exception as e:
            logger.error(f"DataForSEO SERP error: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_search_volume(keywords: list, location_code: int = 2840, language_code: str = "en") -> dict:
        """
        Get search volume, CPC, and competition for keywords.
        Returns dict mapping keyword -> {volume, cpc, competition, trend}.
        """
        headers = DataForSEOService._auth_headers()
        if not headers:
            return {"error": "DataForSEO not configured", "configured": False}

        cache_key = f"dfs_vol_{'_'.join(sorted(keywords[:5]))}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            payload = [{
                "keywords": keywords[:20],
                "location_code": location_code,
                "language_code": language_code,
            }]
            resp = requests.post(
                f"{DATAFORSEO_BASE}/keywords_data/google_ads/search_volume/live",
                headers=headers,
                json=payload,
                timeout=30,
            )
            data = resp.json()

            if data.get("status_code") != 20000:
                return {"error": data.get("status_message", "API error")}

            result = {}
            tasks = data.get("tasks", [])
            if tasks and tasks[0].get("result"):
                for item in tasks[0]["result"]:
                    kw = item.get("keyword", "")
                    monthly = item.get("monthly_searches", [])
                    trend = []
                    if monthly:
                        trend = [{"month": m.get("month"), "year": m.get("year"), "volume": m.get("search_volume", 0)} for m in monthly[:6]]

                    result[kw] = {
                        "volume": item.get("search_volume", 0),
                        "cpc": item.get("cpc", 0),
                        "competition": item.get("competition", 0),
                        "competition_level": item.get("competition_level", ""),
                        "trend": trend,
                    }

            cache.set(cache_key, result, 3600)
            return result

        except Exception as e:
            logger.error(f"DataForSEO volume error: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_keyword_difficulty(keywords: list, location_code: int = 2840, language_code: str = "en") -> dict:
        """
        Get keyword difficulty scores (0-100).
        Returns dict mapping keyword -> {difficulty, serp_data}.
        """
        headers = DataForSEOService._auth_headers()
        if not headers:
            return {"error": "DataForSEO not configured", "configured": False}

        cache_key = f"dfs_diff_{'_'.join(sorted(keywords[:5]))}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            payload = [{
                "keywords": keywords[:20],
                "location_code": location_code,
                "language_code": language_code,
            }]
            resp = requests.post(
                f"{DATAFORSEO_BASE}/dataforseo_labs/google/bulk_keyword_difficulty/live",
                headers=headers,
                json=payload,
                timeout=30,
            )
            data = resp.json()

            if data.get("status_code") != 20000:
                return {"error": data.get("status_message", "API error")}

            result = {}
            tasks = data.get("tasks", [])
            if tasks and tasks[0].get("result"):
                for item in tasks[0]["result"]:
                    kw = item.get("keyword", "")
                    result[kw] = {
                        "difficulty": item.get("keyword_difficulty", 0),
                    }

            cache.set(cache_key, result, 3600)
            return result

        except Exception as e:
            logger.error(f"DataForSEO difficulty error: {e}")
            return {"error": str(e)}

    @staticmethod
    def enrich_keywords(keywords: list, domain: str, location_code: int = 2840) -> list:
        """
        Full enrichment: volume + difficulty + SERP position for each keyword.
        Returns list of enriched keyword dicts.
        """
        if not DataForSEOService.is_configured():
            return [{"keyword": kw, "enriched": False, "error": "DataForSEO not configured"} for kw in keywords]

        kw_list = [k if isinstance(k, str) else k.get("keyword", "") for k in keywords][:12]

        # Batch: volume + difficulty
        volume_data = DataForSEOService.get_search_volume(kw_list, location_code)
        difficulty_data = DataForSEOService.get_keyword_difficulty(kw_list, location_code)

        enriched = []
        for kw in kw_list:
            vol = volume_data.get(kw, {}) if isinstance(volume_data, dict) and "error" not in volume_data else {}
            diff = difficulty_data.get(kw, {}) if isinstance(difficulty_data, dict) and "error" not in difficulty_data else {}

            # SERP ranking for top keywords only (expensive call)
            serp = {}
            if len(enriched) < 6:  # Limit SERP lookups to save credits
                serp = DataForSEOService.get_serp_rankings(kw, domain, location_code)

            enriched.append({
                "keyword": kw,
                "enriched": True,
                "position": serp.get("position"),
                "serp_url": serp.get("url"),
                "serp_title": serp.get("title"),
                "serp_features": serp.get("serp_features", []),
                "top_competitors": serp.get("top_competitors", []),
                "volume": vol.get("volume", 0),
                "cpc": vol.get("cpc", 0),
                "competition": vol.get("competition", 0),
                "competition_level": vol.get("competition_level", ""),
                "difficulty": diff.get("difficulty", 0),
                "volume_trend": vol.get("trend", []),
            })

        return enriched
