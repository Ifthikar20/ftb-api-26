import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from apps.audits.models import Audit, SEOGraderIssue

logger = logging.getLogger("apps")

HEADERS = {"User-Agent": "FetchBot-SEOGrader/1.0"}
MAX_PAGES = 50
TIMEOUT = 15


class SEOGrader:
    """Multi-page SEO grader — crawls all pages, checks categories, generates fixes."""

    @staticmethod
    def run(*, website, audit: Audit) -> dict:
        """Crawl the site and grade every page for SEO issues."""
        base_url = website.url.rstrip("/")
        pages = SEOGrader._discover_pages(base_url)
        if not pages:
            pages = [base_url + "/"]

        total_issues = 0
        total_pages = len(pages)
        flawless = 0
        score = 100
        issues_created = []

        for page_url in pages:
            page_issues = SEOGrader._analyze_page(page_url, base_url, audit)
            issues_created.extend(page_issues)
            if not page_issues:
                flawless += 1
            total_issues += len(page_issues)

        # Score: start at 100, deduct based on issue density
        if total_pages > 0:
            issue_rate = total_issues / total_pages
            penalty = min(70, int(issue_rate * 8))
            score = max(0, 100 - penalty)

        # Save summary to audit raw_data
        grader_summary = {
            "grader_score": score,
            "total_pages": total_pages,
            "total_issues": total_issues,
            "flawless_pages": flawless,
            "deployed_count": 0,
            "not_deployed_count": total_issues,
        }
        audit.raw_data = {**audit.raw_data, "grader": grader_summary}
        audit.save(update_fields=["raw_data"])

        return grader_summary

    @staticmethod
    def _discover_pages(base_url: str) -> list:
        """Discover pages via sitemap then fallback to crawling internal links."""
        pages = set()

        # Try sitemap
        for sitemap_path in ["/sitemap.xml", "/sitemap_index.xml"]:
            try:
                resp = requests.get(base_url + sitemap_path, timeout=TIMEOUT, headers=HEADERS)
                if resp.status_code == 200 and "<loc>" in resp.text:
                    from xml.etree import ElementTree as ET
                    root = ET.fromstring(resp.content)
                    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                    for loc in root.findall(".//s:loc", ns):
                        if loc.text:
                            pages.add(loc.text.rstrip("/") + "/")
                    if pages:
                        break
            except Exception:
                continue

        # Fallback: crawl homepage for internal links
        if not pages:
            try:
                resp = requests.get(base_url + "/", timeout=TIMEOUT, headers=HEADERS)
                soup = BeautifulSoup(resp.text, "html.parser")
                parsed = urlparse(base_url)
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full = urljoin(base_url, href)
                    if urlparse(full).netloc == parsed.netloc:
                        pages.add(full.split("?")[0].split("#")[0].rstrip("/") + "/")
            except Exception:
                pass

        # Always include homepage
        pages.add(base_url + "/")
        return sorted(list(pages))[:MAX_PAGES]

    @staticmethod
    def _analyze_page(page_url: str, base_url: str, audit: Audit) -> list:
        """Analyze a single page for all SEO categories."""
        issues = []
        try:
            resp = requests.get(page_url, timeout=TIMEOUT, headers=HEADERS)
            if resp.status_code != 200:
                return issues
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:
            return issues

        # Relative path for display
        parsed = urlparse(page_url)
        path = parsed.path or "/"

        # ── Page Title ──
        title_tag = soup.find("title")
        title_text = title_tag.string.strip() if title_tag and title_tag.string else ""
        if len(title_text) < 30 or len(title_text) > 60 or not title_text:
            suggested = SEOGrader._suggest_title(title_text, path)
            issues.append(SEOGraderIssue(
                audit=audit, category="page_title", page_url=path,
                original_value=title_text, original_length=len(title_text),
                suggested_fix=suggested, suggested_length=len(suggested),
            ))

        # ── Meta Description ──
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else ""
        if len(desc_text) < 50 or len(desc_text) > 160 or not desc_text:
            suggested = SEOGrader._suggest_meta_desc(desc_text, title_text, path)
            issues.append(SEOGraderIssue(
                audit=audit, category="meta_description", page_url=path,
                original_value=desc_text, original_length=len(desc_text),
                suggested_fix=suggested, suggested_length=len(suggested),
            ))

        # ── Image Alt Text ──
        images = soup.find_all("img")
        for img in images:
            alt = img.get("alt", "").strip()
            src = img.get("src", "")[:200]
            if not alt:
                suggested = SEOGrader._suggest_alt(src, path)
                issues.append(SEOGraderIssue(
                    audit=audit, category="image_alt", page_url=path,
                    original_value=f"[no alt] {src}", original_length=0,
                    suggested_fix=suggested, suggested_length=len(suggested),
                ))

        # ── H1 Length ──
        h1_tags = soup.find_all("h1")
        for h1 in h1_tags:
            h1_text = h1.get_text(strip=True)
            if len(h1_text) < 10 or len(h1_text) > 70:
                issues.append(SEOGraderIssue(
                    audit=audit, category="h1_length", page_url=path,
                    original_value=h1_text, original_length=len(h1_text),
                    suggested_fix="", suggested_length=0,
                ))
        if not h1_tags:
            issues.append(SEOGraderIssue(
                audit=audit, category="h1_length", page_url=path,
                original_value="[missing H1]", original_length=0,
                suggested_fix="", suggested_length=0,
            ))

        # ── H2 Length ──
        h2_tags = soup.find_all("h2")
        for h2 in h2_tags:
            h2_text = h2.get_text(strip=True)
            if len(h2_text) < 5 or len(h2_text) > 70:
                issues.append(SEOGraderIssue(
                    audit=audit, category="h2_length", page_url=path,
                    original_value=h2_text, original_length=len(h2_text),
                    suggested_fix="", suggested_length=0,
                ))

        # ── Canonical Link ──
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical or not canonical.get("href"):
            issues.append(SEOGraderIssue(
                audit=audit, category="canonical_link", page_url=path,
                original_value="[missing]", original_length=0,
                suggested_fix=page_url, suggested_length=len(page_url),
            ))

        # ── OG Tags ──
        for og_prop, cat in [("og:title", "og_title"), ("og:description", "og_description"), ("og:url", "og_url")]:
            og = soup.find("meta", attrs={"property": og_prop})
            if not og or not og.get("content"):
                issues.append(SEOGraderIssue(
                    audit=audit, category=cat, page_url=path,
                    original_value="[missing]", original_length=0,
                    suggested_fix="", suggested_length=0,
                ))

        # ── Twitter Tags ──
        for tw_name, cat in [("twitter:title", "twitter_title"), ("twitter:description", "twitter_description"),
                             ("twitter:site", "twitter_site"), ("twitter:card", "twitter_card")]:
            tw = soup.find("meta", attrs={"name": tw_name}) or soup.find("meta", attrs={"property": tw_name})
            if not tw or not tw.get("content"):
                issues.append(SEOGraderIssue(
                    audit=audit, category=cat, page_url=path,
                    original_value="[missing]", original_length=0,
                    suggested_fix="summary_large_image" if cat == "twitter_card" else "",
                    suggested_length=0,
                ))

        # ── Lang Missing ──
        html_tag = soup.find("html")
        if not html_tag or not html_tag.get("lang"):
            issues.append(SEOGraderIssue(
                audit=audit, category="lang_missing", page_url=path,
                original_value="[missing]", original_length=0,
                suggested_fix="en", suggested_length=2,
            ))

        # ── Meta Keywords ──
        meta_kw = soup.find("meta", attrs={"name": "keywords"})
        if not meta_kw or not meta_kw.get("content"):
            issues.append(SEOGraderIssue(
                audit=audit, category="meta_keywords", page_url=path,
                original_value="[missing]", original_length=0,
                suggested_fix="", suggested_length=0,
            ))

        # ── Internal Linking ──
        links = soup.find_all("a", href=True)
        base_parsed = urlparse(base_url)
        internal = [a for a in links if urlparse(urljoin(base_url, a["href"])).netloc == base_parsed.netloc]
        if len(internal) < 2:
            issues.append(SEOGraderIssue(
                audit=audit, category="internal_linking", page_url=path,
                original_value=f"{len(internal)} internal links found",
                original_length=len(internal),
                suggested_fix="Add 3+ contextual internal links",
                suggested_length=0,
            ))

        # ── Organization Schema ──
        schemas = soup.find_all("script", attrs={"type": "application/ld+json"})
        has_org = False
        for s in schemas:
            try:
                import json
                data = json.loads(s.string or "")
                if isinstance(data, dict) and data.get("@type") in ("Organization", "WebSite", "LocalBusiness"):
                    has_org = True
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") in ("Organization", "WebSite", "LocalBusiness"):
                            has_org = True
            except Exception:
                pass
        if not has_org and path == "/":
            issues.append(SEOGraderIssue(
                audit=audit, category="organization_schema", page_url=path,
                original_value="[missing]", original_length=0,
                suggested_fix="Add Organization or WebSite JSON-LD schema",
                suggested_length=0,
            ))

        # Bulk create
        if issues:
            SEOGraderIssue.objects.bulk_create(issues)

        return issues

    # ── Suggestion helpers ──
    @staticmethod
    def _suggest_title(original: str, path: str) -> str:
        """Generate a suggested title based on the path and original."""
        if not original:
            parts = [p for p in path.strip("/").split("/") if p]
            if parts:
                readable = " ".join(p.replace("-", " ").replace("_", " ").title() for p in parts)
                return f"{readable} | Your Site"
            return ""
        # If too short/long, optimize
        if len(original) < 30:
            return f"{original}: Expert Guide & Tips | Your Site"
        if len(original) > 60:
            return original[:57] + "..."
        return original

    @staticmethod
    def _suggest_meta_desc(original: str, title: str, path: str) -> str:
        """Generate a suggested meta description."""
        if not original and title:
            return f"Discover {title.lower()}. Get expert insights, tips, and detailed information. Learn more today."
        if not original:
            parts = [p for p in path.strip("/").split("/") if p]
            readable = " ".join(p.replace("-", " ") for p in parts) if parts else "our content"
            return f"Explore {readable}. Find expert insights and helpful resources to guide your journey."
        return original

    @staticmethod
    def _suggest_alt(src: str, path: str) -> str:
        """Generate a suggested alt text from image src."""
        # Extract filename
        name = src.split("/")[-1].split("?")[0] if src else ""
        name = re.sub(r"\.\w{2,4}$", "", name)
        name = name.replace("-", " ").replace("_", " ")
        if name and len(name) > 3:
            return name.title()
        return "Descriptive alt text needed"
