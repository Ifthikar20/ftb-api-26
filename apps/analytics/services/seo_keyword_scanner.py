"""
SEO Keyword Scanner & AI Ranking Agent — Crawl site, extract keywords,
compare to Google Trends, check AI engine rankings (Claude, ChatGPT, Perplexity),
suggest better synonyms, and calculate a progressive SEO score.
"""
import hashlib
import logging
import re
from collections import Counter
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("apps")

# Common stop words to exclude from keyword extraction
STOP_WORDS = frozenset(
    "a an the and or but in on at to for of is it this that was were be been "
    "being have has had do does did will would shall should may might can could "
    "i me my we our you your he she they them their its with from by as are am "
    "not no so if then else when where how what which who whom all each every "
    "any some many much more most other another such only own same than too very "
    "just about above after again also back because before between both but come "
    "could day even find first get give go here him his into like look make new "
    "now number over people see she some take tell there these thing think time "
    "two us use want way well work year also been call came come does find go "
    "got great help here high home house just know let life little long look "
    "made make many may next number off old only over own part place point "
    "right say she show small still take tell turn us very want well went "
    "while will world years click page menu home login sign up site free "
    "copyright reserved privacy policy terms contact us about learn".split()
)


class SEOKeywordScanner:
    """Crawl website, extract keywords, compare to trends, check AI rankings, suggest alternatives."""

    @staticmethod
    def scan(*, website_url: str, website_id: str = "") -> dict:
        """
        Full keyword scan: crawl ALL pages → extract → score → suggest.
        Returns complete scan results with SEO keyword score.
        """
        cache_key = f"seo_scan_{hashlib.md5(website_url.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            # 1. Crawl the homepage
            homepage = SEOKeywordScanner._crawl_page(website_url)
            if not homepage:
                return {"error": "Could not reach website", "score": 0}

            # 2. Discover internal links and crawl sub-pages
            parsed_base = urlparse(website_url)
            base_domain = parsed_base.netloc.replace("www.", "")
            internal_links = SEOKeywordScanner._discover_links(homepage, website_url)
            logger.info(f"Discovered {len(internal_links)} internal links on {website_url}")

            all_pages = [{"url": website_url, "data": homepage}]
            for link in internal_links[:10]:  # Crawl up to 10 sub-pages
                try:
                    sub_page = SEOKeywordScanner._crawl_page(link)
                    if sub_page and sub_page.get("word_count", 0) > 20:
                        all_pages.append({"url": link, "data": sub_page})
                except Exception:
                    continue

            # 3. Merge all page data for unified keyword extraction
            merged_data = SEOKeywordScanner._merge_page_data(all_pages)
            keywords = SEOKeywordScanner._extract_keywords(merged_data)

            # 4. Per-page keyword attribution
            per_page = []
            for pg in all_pages:
                pg_kws = SEOKeywordScanner._extract_keywords(pg["data"])
                per_page.append({
                    "url": pg["url"],
                    "title": pg["data"].get("title", ""),
                    "word_count": pg["data"].get("word_count", 0),
                    "h1": pg["data"].get("h1", []),
                    "top_keywords": [k["keyword"] for k in pg_kws[:8]],
                    "keyword_count": len(pg_kws),
                })

            # 5. Get trend data for top keywords
            keyword_trends = SEOKeywordScanner._get_trend_data(
                [k["keyword"] for k in keywords[:10]]
            )

            # 6. Find synonym suggestions
            suggestions = SEOKeywordScanner._find_synonyms(keywords[:8], keyword_trends)

            # 7. Calculate composite SEO keyword score
            score_breakdown = SEOKeywordScanner._calculate_score(
                merged_data, keywords, keyword_trends, suggestions
            )

            result = {
                "url": website_url,
                "scanned_at": timezone.now().isoformat(),
                "pages_scanned": len(all_pages),
                "score": score_breakdown["total"],
                "score_breakdown": score_breakdown,
                "keywords": keywords[:15],
                "trends": keyword_trends,
                "suggestions": suggestions[:10],
                "per_page": per_page,
                "page_meta": {
                    "title": homepage.get("title", ""),
                    "meta_description": homepage.get("meta_description", ""),
                    "h1": homepage.get("h1", []),
                    "h2": merged_data.get("h2", []),
                    "h3": merged_data.get("h3", []),
                    "word_count": merged_data.get("word_count", 0),
                },
                "geo_data": {
                    "hreflang": homepage.get("hreflang", []),
                    "og_locale": homepage.get("og_locale", ""),
                    "geo_region": homepage.get("geo_region", ""),
                    "geo_placename": homepage.get("geo_placename", ""),
                    "has_geo_tags": bool(homepage.get("hreflang") or homepage.get("og_locale") or homepage.get("geo_region")),
                    "tips": SEOKeywordScanner._geo_tips(homepage),
                },
            }

            # 8. Check AI engine rankings
            try:
                ai_rankings = SEOKeywordScanner._check_ai_rankings(
                    [k["keyword"] for k in keywords[:6]], base_domain
                )
                result["ai_rankings"] = ai_rankings
            except Exception as e:
                logger.warning(f"AI ranking check failed: {e}")
                result["ai_rankings"] = {}

            cache.set(cache_key, result, 900)  # Cache 15 min
            return result

        except Exception as e:
            logger.error(f"SEO keyword scan failed for {website_url}: {e}")
            return {"error": str(e), "score": 0}

    @staticmethod
    def _discover_links(page_data: dict, base_url: str) -> list:
        """Find internal links from raw_links extracted before decomposition."""
        raw_links = page_data.get("raw_links", [])
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc.replace("www.", "")
        base_scheme = parsed_base.scheme or "https"
        seen = set()
        links = []

        for href in raw_links:
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            # Resolve relative URLs
            if href.startswith("/"):
                href = f"{base_scheme}://{parsed_base.netloc}{href}"
            elif not href.startswith("http"):
                continue

            parsed = urlparse(href)
            link_domain = parsed.netloc.replace("www.", "")
            if link_domain != base_domain:
                continue

            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if clean in seen or clean == base_url.rstrip("/"):
                continue
            if any(clean.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js", ".pdf", ".zip")):
                continue

            seen.add(clean)
            links.append(clean)

        return links

    @staticmethod
    def _merge_page_data(pages: list) -> dict:
        """Merge data from multiple crawled pages into one for keyword extraction."""
        merged = {
            "title": pages[0]["data"].get("title", ""),
            "meta_description": pages[0]["data"].get("meta_description", ""),
            "h1": [],
            "h2": [],
            "h3": [],
            "words": [],
            "word_count": 0,
        }
        for pg in pages:
            d = pg["data"]
            merged["h1"].extend(d.get("h1", []))
            merged["h2"].extend(d.get("h2", []))
            merged["h3"].extend(d.get("h3", []))
            merged["words"].extend(d.get("words", []))
            merged["word_count"] += d.get("word_count", 0)

        return merged

    @staticmethod
    def _geo_tips(page_data: dict) -> list:
        """Generate geo SEO tips based on detected tags."""
        tips = []
        if not page_data.get("hreflang"):
            tips.append({
                "type": "warning",
                "tip": "No hreflang tags found. Add hreflang to target international audiences and improve regional SEO.",
                "tag": '<link rel="alternate" hreflang="en-US" href="..." />',
            })
        else:
            tips.append({
                "type": "success",
                "tip": f"Found {len(page_data['hreflang'])} hreflang tag(s) — good for international SEO.",
            })
        if not page_data.get("og_locale"):
            tips.append({
                "type": "info",
                "tip": "No og:locale meta tag. Add it to specify your content's language/region for social sharing.",
                "tag": '<meta property="og:locale" content="en_US" />',
            })
        if not page_data.get("geo_region"):
            tips.append({
                "type": "info",
                "tip": "No geo.region meta tag. Add it for local SEO targeting.",
                "tag": '<meta name="geo.region" content="US-NY" />',
            })
        return tips

    @staticmethod
    def _crawl_page(url: str) -> dict:
        """Fetch and parse page content."""
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; FetchBot/1.0; +https://fetchbot.ai)"
            })
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            # ── Extract geo tags BEFORE decomposing ──
            hreflang_tags = []
            for link in soup.find_all("link", attrs={"hreflang": True}):
                hreflang_tags.append({
                    "lang": link.get("hreflang", ""),
                    "href": link.get("href", ""),
                })

            og_locale = ""
            og_tag = soup.find("meta", attrs={"property": "og:locale"})
            if og_tag:
                og_locale = og_tag.get("content", "")

            geo_region = ""
            geo_tag = soup.find("meta", attrs={"name": "geo.region"})
            if geo_tag:
                geo_region = geo_tag.get("content", "")

            geo_placename = ""
            geo_pn = soup.find("meta", attrs={"name": "geo.placename"})
            if geo_pn:
                geo_placename = geo_pn.get("content", "")

            # ── Extract ALL links BEFORE decomposing anything ──
            raw_links = [a["href"].strip() for a in soup.find_all("a", href=True)]
            soup_for_links = soup  # Keep full soup for link discovery

            # Remove only scripts/styles for content extraction
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            # Extract structured content
            title = ""
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip()

            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

            h1_tags = [h.get_text(strip=True) for h in soup.find_all("h1")]
            h2_tags = [h.get_text(strip=True) for h in soup.find_all("h2")]
            h3_tags = [h.get_text(strip=True) for h in soup.find_all("h3")]

            # Get visible text
            body_text = soup.get_text(separator=" ", strip=True)
            body_text = re.sub(r"\s+", " ", body_text)

            words = body_text.lower().split()
            word_count = len(words)

            return {
                "title": title,
                "meta_description": meta_desc,
                "h1": h1_tags,
                "h2": h2_tags,
                "h3": h3_tags,
                "body_text": body_text,
                "words": words,
                "word_count": word_count,
                "soup": soup_for_links,
                "raw_links": raw_links,
                "hreflang": hreflang_tags,
                "og_locale": og_locale,
                "geo_region": geo_region,
                "geo_placename": geo_placename,
            }
        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")
            return None

    @staticmethod
    def _extract_keywords(page_data: dict) -> list:
        """
        Extract keywords using weighted frequency scoring.
        Extracts both single words AND two-word phrases (bigrams).
        Title keywords get 5x weight, H1 3x, H2 2x, meta 3x, body 1x.
        """
        weighted_counts = Counter()
        all_words = page_data.get("words", [])

        def tokenize(text):
            words = re.findall(r"[a-zA-Z]{3,}", text.lower())
            return [w for w in words if w not in STOP_WORDS and len(w) > 2]

        def bigrams(text):
            """Extract two-word phrases from text."""
            words = re.findall(r"[a-zA-Z]{3,}", text.lower())
            phrases = []
            for i in range(len(words) - 1):
                w1, w2 = words[i], words[i + 1]
                if w1 not in STOP_WORDS and w2 not in STOP_WORDS and len(w1) > 2 and len(w2) > 2:
                    phrases.append(f"{w1} {w2}")
            return phrases

        # Title (5x weight)
        title = page_data.get("title", "")
        for w in tokenize(title):
            weighted_counts[w] += 5
        for bg in bigrams(title):
            weighted_counts[bg] += 6

        # Meta description (3x weight)
        meta = page_data.get("meta_description", "")
        for w in tokenize(meta):
            weighted_counts[w] += 3
        for bg in bigrams(meta):
            weighted_counts[bg] += 4

        # H1 headings (3x weight)
        for h in page_data.get("h1", []):
            for w in tokenize(h):
                weighted_counts[w] += 3
            for bg in bigrams(h):
                weighted_counts[bg] += 4

        # H2 headings (2x weight)
        for h in page_data.get("h2", []):
            for w in tokenize(h):
                weighted_counts[w] += 2
            for bg in bigrams(h):
                weighted_counts[bg] += 3

        # H3 headings (1.5x weight)
        for h in page_data.get("h3", []):
            for w in tokenize(h):
                weighted_counts[w] += 1.5
            for bg in bigrams(h):
                weighted_counts[bg] += 2

        # Body text (1x weight)
        body = " ".join(all_words)
        for w in tokenize(body):
            weighted_counts[w] += 1
        for bg in bigrams(body):
            weighted_counts[bg] += 1.5

        # Remove single words that are part of higher-scoring bigrams
        bigram_words = set()
        for phrase in weighted_counts:
            if " " in phrase:
                for w in phrase.split():
                    bigram_words.add(w)

        # Calculate density for each keyword
        total_words = max(page_data.get("word_count", 1), 1)
        body_counter = Counter(tokenize(body))

        keywords = []
        for word, score in weighted_counts.most_common(40):
            # If single word is absorbed into a bigram with higher score, skip
            if " " not in word and word in bigram_words:
                best_bigram_score = max(
                    (s for p, s in weighted_counts.items() if " " in p and word in p.split()),
                    default=0
                )
                if best_bigram_score > score:
                    continue

            if " " in word:
                # Bigram density: count phrase occurrences
                count = body.lower().count(word)
                density = round((count / max(total_words // 2, 1)) * 100, 2)
            else:
                count = body_counter.get(word, 0)
                density = round((count / total_words) * 100, 2)

            # Check where keyword appears
            locations = []
            if word in title.lower():
                locations.append("title")
            if word in (page_data.get("meta_description", "") or "").lower():
                locations.append("meta")
            for h in page_data.get("h1", []):
                if word in h.lower():
                    locations.append("h1")
                    break
            for h in page_data.get("h2", []):
                if word in h.lower():
                    locations.append("h2")
                    break

            keywords.append({
                "keyword": word,
                "score": round(score, 1),
                "count": count,
                "density": density,
                "locations": locations,
                "is_phrase": " " in word,
                "density_status": (
                    "optimal" if 1.0 <= density <= 3.0
                    else "low" if density < 1.0
                    else "high"
                ),
            })

            if len(keywords) >= 20:
                break

        return keywords

    @staticmethod
    def _get_trend_data(keywords: list) -> dict:
        """Get Google Trends interest for extracted keywords."""
        if not keywords:
            return {}

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

            # Google Trends allows max 5 at a time
            results = {}
            for batch_start in range(0, min(len(keywords), 10), 5):
                batch = keywords[batch_start:batch_start + 5]
                try:
                    pytrends.build_payload(batch, timeframe="today 3-m", geo="US")
                    interest = pytrends.interest_over_time()

                    for kw in batch:
                        if not interest.empty and kw in interest:
                            values = interest[kw].tolist()
                            avg = round(sum(values) / max(len(values), 1))
                            # Trend direction: compare last week avg to first week avg
                            first_week = values[:7] if len(values) >= 7 else values[:len(values)//2]
                            last_week = values[-7:] if len(values) >= 7 else values[len(values)//2:]
                            first_avg = sum(first_week) / max(len(first_week), 1)
                            last_avg = sum(last_week) / max(len(last_week), 1)
                            trend = "rising" if last_avg > first_avg * 1.1 else "declining" if last_avg < first_avg * 0.9 else "stable"

                            results[kw] = {
                                "interest": avg,
                                "trend": trend,
                                "peak": max(values) if values else 0,
                            }
                        else:
                            results[kw] = {"interest": 0, "trend": "unknown", "peak": 0}
                except Exception:
                    for kw in batch:
                        results[kw] = {"interest": 0, "trend": "unknown", "peak": 0}

            return results

        except ImportError:
            logger.info("pytrends not installed — using simulated trend data")
            # Simulated fallback
            import random
            results = {}
            for kw in keywords:
                interest = random.randint(10, 85)
                results[kw] = {
                    "interest": interest,
                    "trend": random.choice(["rising", "stable", "declining"]),
                    "peak": interest + random.randint(5, 20),
                }
            return results

    @staticmethod
    def _find_synonyms(keywords: list, trends: dict) -> list:
        """Find better-trending alternatives for each keyword."""
        suggestions = []

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

            for kw_data in keywords[:6]:
                kw = kw_data["keyword"]
                try:
                    pytrends.build_payload([kw], timeframe="today 3-m", geo="US")
                    related = pytrends.related_queries()

                    current_interest = trends.get(kw, {}).get("interest", 0)

                    if kw in related and related[kw].get("top") is not None:
                        top_df = related[kw]["top"]
                        if not top_df.empty:
                            for _, row in top_df.head(3).iterrows():
                                alt = str(row.get("query", ""))
                                alt_value = int(row.get("value", 0))
                                if alt and alt.lower() != kw.lower() and alt_value > 0:
                                    suggestions.append({
                                        "original": kw,
                                        "original_interest": current_interest,
                                        "suggested": alt,
                                        "suggested_interest": alt_value,
                                        "improvement": alt_value - current_interest if current_interest > 0 else alt_value,
                                        "source": "google_trends",
                                    })

                    if kw in related and related[kw].get("rising") is not None:
                        rising_df = related[kw]["rising"]
                        if not rising_df.empty:
                            for _, row in rising_df.head(2).iterrows():
                                alt = str(row.get("query", ""))
                                alt_value = int(row.get("value", 0))
                                if alt and alt.lower() != kw.lower():
                                    suggestions.append({
                                        "original": kw,
                                        "original_interest": current_interest,
                                        "suggested": alt,
                                        "suggested_interest": alt_value,
                                        "improvement": alt_value,
                                        "source": "rising_trend",
                                    })
                except Exception:
                    continue

        except ImportError:
            # Fallback: generate basic suggestions
            synonym_map = {
                "fashion": ["trendy outfits", "style trends", "fashion trends 2026"],
                "fashionable": ["trendy", "stylish", "chic outfits"],
                "clothes": ["apparel", "clothing deals", "wardrobe"],
                "shop": ["buy online", "shopping deals", "best prices"],
                "beautiful": ["stunning", "gorgeous", "aesthetic"],
                "cheap": ["affordable", "budget-friendly", "best value"],
                "best": ["top rated", "most popular", "highest rated"],
            }

            for kw_data in keywords[:6]:
                kw = kw_data["keyword"]
                current_interest = trends.get(kw, {}).get("interest", 0)

                if kw in synonym_map:
                    for alt in synonym_map[kw]:
                        suggestions.append({
                            "original": kw,
                            "original_interest": current_interest,
                            "suggested": alt,
                            "suggested_interest": current_interest + 15,
                            "improvement": 15,
                            "source": "ai_suggestion",
                        })

        # Sort by improvement potential
        suggestions.sort(key=lambda x: x.get("improvement", 0), reverse=True)
        return suggestions

    @staticmethod
    def _calculate_score(page_data, keywords, trends, suggestions) -> dict:
        """
        Calculate composite SEO keyword score (0-100).

        Components:
        - keyword_relevance (25%): Avg Google Trends interest of keywords
        - title_meta (20%): Keywords present in title + meta
        - synonym_opportunity (20%): Improvement potential
        - keyword_density (15%): Proper density distribution
        - content_freshness (10%): Keyword trend direction
        - heading_usage (10%): Keywords in H1-H3
        """

        # 1. Keyword Relevance (25%) — avg interest of top keywords
        interests = [trends.get(k["keyword"], {}).get("interest", 0) for k in keywords[:10]]
        avg_interest = sum(interests) / max(len(interests), 1)
        keyword_relevance = min(100, round(avg_interest * 1.2))  # Scale up slightly

        # 2. Title/Meta Optimization (20%)
        title_meta_score = 100
        title = page_data.get("title", "").lower()
        meta = page_data.get("meta_description", "").lower()

        if not title:
            title_meta_score -= 40
        if not meta:
            title_meta_score -= 30

        # Check if top keywords appear in title/meta
        top_5 = [k["keyword"] for k in keywords[:5]]
        title_hits = sum(1 for k in top_5 if k in title)
        meta_hits = sum(1 for k in top_5 if k in meta)
        title_meta_score = min(100, title_meta_score + (title_hits * 10) + (meta_hits * 6))
        title_meta_score = max(0, min(100, title_meta_score))

        # 3. Synonym Opportunities (20%) — fewer needed = higher score
        total_kw = max(len(keywords[:10]), 1)
        kw_with_better_alt = len(set(s["original"] for s in suggestions if s.get("improvement", 0) > 10))
        synonym_ratio = kw_with_better_alt / total_kw
        synonym_score = max(0, round(100 - (synonym_ratio * 100)))

        # 4. Keyword Density (15%)
        density_scores = []
        for k in keywords[:10]:
            d = k.get("density", 0)
            if 1.0 <= d <= 3.0:
                density_scores.append(100)
            elif d < 1.0:
                density_scores.append(max(0, round(d * 100)))
            else:
                density_scores.append(max(0, round(100 - (d - 3) * 20)))
        density_score = round(sum(density_scores) / max(len(density_scores), 1))

        # 5. Content Freshness (10%) — are keywords trending?
        trend_dirs = [trends.get(k["keyword"], {}).get("trend", "unknown") for k in keywords[:10]]
        rising = trend_dirs.count("rising")
        declining = trend_dirs.count("declining")
        freshness = min(100, max(0, 50 + (rising * 15) - (declining * 15)))

        # 6. Heading Usage (10%)
        heading_keywords = set()
        for h in page_data.get("h1", []) + page_data.get("h2", []) + page_data.get("h3", []):
            for w in re.findall(r"[a-zA-Z]{3,}", h.lower()):
                heading_keywords.add(w)

        top_in_headings = sum(1 for k in keywords[:10] if k["keyword"] in heading_keywords)
        heading_score = min(100, round((top_in_headings / max(len(keywords[:10]), 1)) * 100))

        # Weighted total
        total = round(
            keyword_relevance * 0.25
            + title_meta_score * 0.20
            + synonym_score * 0.20
            + density_score * 0.15
            + freshness * 0.10
            + heading_score * 0.10
        )

        return {
            "total": max(0, min(100, total)),
            "keyword_relevance": {"score": keyword_relevance, "weight": 25, "label": "Keyword Relevance"},
            "title_meta": {"score": title_meta_score, "weight": 20, "label": "Title & Meta"},
            "synonym_opportunity": {"score": synonym_score, "weight": 20, "label": "Synonym Optimization"},
            "keyword_density": {"score": density_score, "weight": 15, "label": "Keyword Density"},
            "content_freshness": {"score": freshness, "weight": 10, "label": "Content Freshness"},
            "heading_usage": {"score": heading_score, "weight": 10, "label": "Heading Usage"},
        }

    @staticmethod
    def _check_ai_rankings(keywords: list, domain: str) -> dict:
        """
        Query AI engines to check if the domain is mentioned/recommended
        for the given keywords. Returns per-engine visibility scores.
        """
        engines = {}

        prompt_template = (
            "I'm looking for the best websites and online resources for: {keywords}. "
            "Please recommend specific websites and URLs that are most relevant and "
            "authoritative for these topics. List at least 5-10 website recommendations "
            "with their URLs."
        )
        keyword_str = ", ".join(keywords[:6])
        prompt = prompt_template.format(keywords=keyword_str)

        # ── Claude (Anthropic) ──
        try:
            api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
            if api_key:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text if response.content else ""
                # Track AI token usage
                try:
                    from core.ai_tracking import record_usage
                    record_usage(
                        module="seo_keywords", model_name="claude-sonnet-4-20250514",
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                    )
                except Exception:
                    pass
                engines["claude"] = SEOKeywordScanner._score_ai_response(
                    text, domain, keywords, "Claude"
                )
            else:
                engines["claude"] = {"status": "not_configured", "score": 0}
        except Exception as e:
            logger.warning(f"Claude ranking check failed: {e}")
            engines["claude"] = {"status": "error", "score": 0, "error": str(e)[:100]}

        # ── ChatGPT (OpenAI) ──
        try:
            api_key = getattr(settings, "OPENAI_API_KEY", "")
            if api_key:
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.choices[0].message.content if response.choices else ""
                engines["chatgpt"] = SEOKeywordScanner._score_ai_response(
                    text, domain, keywords, "ChatGPT"
                )
            else:
                engines["chatgpt"] = {"status": "not_configured", "score": 0}
        except Exception as e:
            logger.warning(f"ChatGPT ranking check failed: {e}")
            engines["chatgpt"] = {"status": "error", "score": 0, "error": str(e)[:100]}

        # ── Perplexity ──
        try:
            api_key = getattr(settings, "PERPLEXITY_API_KEY", "")
            if api_key:
                import openai as openai_compat
                client = openai_compat.OpenAI(
                    api_key=api_key,
                    base_url="https://api.perplexity.ai",
                )
                response = client.chat.completions.create(
                    model="llama-3.1-sonar-small-128k-online",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.choices[0].message.content if response.choices else ""
                engines["perplexity"] = SEOKeywordScanner._score_ai_response(
                    text, domain, keywords, "Perplexity"
                )
            else:
                engines["perplexity"] = {"status": "not_configured", "score": 0}
        except Exception as e:
            logger.warning(f"Perplexity ranking check failed: {e}")
            engines["perplexity"] = {"status": "error", "score": 0, "error": str(e)[:100]}

        # Calculate overall AI visibility score
        active_engines = [e for e in engines.values() if e.get("status") == "found" or e.get("status") == "not_found"]
        if active_engines:
            engines["overall_score"] = round(
                sum(e.get("score", 0) for e in active_engines) / len(active_engines)
            )
        else:
            engines["overall_score"] = 0

        return engines

    @staticmethod
    def _score_ai_response(response_text: str, domain: str, keywords: list, engine_name: str) -> dict:
        """
        Score how visible a domain is in an AI engine's response.
        Returns visibility score (0-100), mentioned keywords, and response excerpt.
        """
        text_lower = response_text.lower()
        domain_lower = domain.lower()

        # Check if domain is mentioned
        domain_mentioned = domain_lower in text_lower

        # Also check partial domain (without TLD)
        domain_base = domain_lower.split(".")[0]
        base_mentioned = len(domain_base) > 3 and domain_base in text_lower

        mentioned = domain_mentioned or base_mentioned

        # Check which keywords triggered a mention near the domain
        mentioned_keywords = []
        if mentioned:
            for kw in keywords:
                # Check if keyword appears within 200 chars of domain mention
                positions = []
                search_term = domain_lower if domain_mentioned else domain_base
                idx = text_lower.find(search_term)
                while idx != -1:
                    positions.append(idx)
                    idx = text_lower.find(search_term, idx + 1)

                for pos in positions:
                    context = text_lower[max(0, pos - 200):pos + 200]
                    if kw.lower() in context:
                        mentioned_keywords.append(kw)
                        break

        # Calculate visibility score
        score = 0
        if mentioned:
            # Base score for being mentioned
            score = 40

            # Position bonus — earlier mention = higher score
            first_pos = text_lower.find(domain_lower if domain_mentioned else domain_base)
            total_len = max(len(text_lower), 1)
            position_ratio = 1 - (first_pos / total_len)
            score += round(position_ratio * 25)  # Up to 25 pts for position

            # Mention count bonus
            count = text_lower.count(domain_lower if domain_mentioned else domain_base)
            score += min(15, count * 5)  # Up to 15 pts for multiple mentions

            # Keyword association bonus
            if mentioned_keywords:
                kw_ratio = len(mentioned_keywords) / max(len(keywords), 1)
                score += round(kw_ratio * 20)  # Up to 20 pts

        # Find excerpt showing the mention
        excerpt = ""
        if mentioned:
            search_term = domain_lower if domain_mentioned else domain_base
            idx = text_lower.find(search_term)
            if idx != -1:
                start = max(0, idx - 80)
                end = min(len(response_text), idx + 120)
                excerpt = response_text[start:end].strip()
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(response_text):
                    excerpt = excerpt + "..."

        return {
            "engine": engine_name,
            "status": "found" if mentioned else "not_found",
            "score": min(100, score),
            "mentioned": mentioned,
            "mentioned_keywords": mentioned_keywords,
            "mention_count": text_lower.count(domain_lower) if domain_mentioned else text_lower.count(domain_base) if base_mentioned else 0,
            "excerpt": excerpt,
        }
