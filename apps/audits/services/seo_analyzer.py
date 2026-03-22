import logging
import re

import requests
from bs4 import BeautifulSoup

from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class SEOAnalyzer:
    """Comprehensive SEO analysis: meta tags, headings, images, canonicals, structured data, sitemap."""

    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        score = 100
        try:
            response = requests.get(website.url, timeout=20, headers={
                "User-Agent": "FetchBot-Audit/1.0 (SEO Analyzer)"
            })
            soup = BeautifulSoup(response.text, "html.parser")
            url = website.url.rstrip("/")

            # ── Title Tag ──
            title_tag = soup.find("title")
            if not title_tag or not title_tag.string:
                score -= 15
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="critical",
                    title="Missing title tag",
                    description="No <title> tag found on the homepage. Search engines rely heavily on title tags for indexing.",
                    recommendation="Add a descriptive title tag with 50-60 characters including your primary keyword.",
                    impact_score=15, element="<head>",
                )
            elif title_tag.string and len(title_tag.string.strip()) > 60:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="warning",
                    title="Title tag too long",
                    description=f"Title is {len(title_tag.string.strip())} characters. Google truncates titles over 60 chars.",
                    recommendation="Shorten your title to 50-60 characters for full visibility in SERPs.",
                    impact_score=5, element=f"<title>{title_tag.string.strip()[:80]}...</title>",
                )
            elif title_tag.string and len(title_tag.string.strip()) < 20:
                score -= 3
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="info",
                    title="Title tag too short",
                    description=f"Title is only {len(title_tag.string.strip())} characters. More descriptive titles rank better.",
                    recommendation="Expand your title to 50-60 characters with relevant keywords.",
                    impact_score=3, element=f"<title>{title_tag.string.strip()}</title>",
                )

            # ── Meta Description ──
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if not meta_desc or not meta_desc.get("content"):
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="warning",
                    title="Missing meta description",
                    description="No meta description found. This is the snippet shown in search results.",
                    recommendation="Add a compelling meta description with 150-160 characters that includes your target keyword.",
                    impact_score=10, element="<head>",
                )
            elif meta_desc.get("content") and len(meta_desc["content"]) > 160:
                score -= 3
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="info",
                    title="Meta description too long",
                    description=f"Meta description is {len(meta_desc['content'])} characters. Google truncates at ~160.",
                    recommendation="Shorten meta description to 150-160 characters.",
                    impact_score=3,
                )

            # ── Heading Hierarchy ──
            h1_tags = soup.find_all("h1")
            if not h1_tags:
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="critical",
                    title="Missing H1 heading",
                    description="No H1 tag found. Every page should have exactly one H1 heading.",
                    recommendation="Add a single, descriptive H1 heading that includes your primary keyword.",
                    impact_score=10,
                )
            elif len(h1_tags) > 1:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="warning",
                    title=f"Multiple H1 tags ({len(h1_tags)} found)",
                    description="Having multiple H1 tags dilutes your page's topic signal to search engines.",
                    recommendation="Use exactly one H1 per page. Use H2-H6 for sub-sections.",
                    impact_score=5,
                )

            # Check heading order (H1 should come before H2, etc.)
            headings = soup.find_all(re.compile(r"^h[1-6]$"))
            prev_level = 0
            for h in headings:
                level = int(h.name[1])
                if level > prev_level + 1 and prev_level > 0:
                    score -= 3
                    AuditIssue.objects.create(
                        audit=audit, category="seo", severity="info",
                        title=f"Broken heading hierarchy: H{prev_level} jumps to H{level}",
                        description=f"Headings skip from H{prev_level} to H{level}. This hurts accessibility and SEO.",
                        recommendation=f"Add an H{prev_level + 1} before your H{level} to maintain proper hierarchy.",
                        impact_score=3, element=str(h)[:200],
                    )
                    break
                prev_level = level

            # ── Image Alt Text ──
            images = soup.find_all("img")
            missing_alt = [img for img in images if not img.get("alt")]
            if missing_alt:
                pct = round(len(missing_alt) / max(len(images), 1) * 100)
                penalty = min(15, len(missing_alt) * 2)
                score -= penalty
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="warning" if len(missing_alt) <= 3 else "critical",
                    title=f"{len(missing_alt)} of {len(images)} images missing alt text ({pct}%)",
                    description="Images without alt text can't be indexed by search engines and hurt accessibility.",
                    recommendation="Add descriptive alt text to all images. Describe the image content and include keywords where relevant.",
                    impact_score=penalty,
                    element=str(missing_alt[0])[:300] if missing_alt else "",
                )

            # ── Canonical URL ──
            canonical = soup.find("link", attrs={"rel": "canonical"})
            if not canonical:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="warning",
                    title="Missing canonical URL",
                    description="No canonical link tag found. This can cause duplicate content issues.",
                    recommendation='Add <link rel="canonical" href="your-page-url"> to prevent duplicate content.',
                    impact_score=5,
                )

            # ── Structured Data (Schema.org) ──
            schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
            if not schema_scripts:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="info",
                    title="No structured data (Schema.org) found",
                    description="Structured data helps search engines understand your content and enables rich snippets.",
                    recommendation="Add JSON-LD structured data for Organization, WebSite, or relevant schema types.",
                    impact_score=5,
                )

            # ── Sitemap ──
            try:
                sitemap_resp = requests.head(f"{url}/sitemap.xml", timeout=10)
                if sitemap_resp.status_code != 200:
                    score -= 5
                    AuditIssue.objects.create(
                        audit=audit, category="seo", severity="warning",
                        title="Sitemap not found at /sitemap.xml",
                        description="No sitemap detected. Sitemaps help search engines discover all your pages.",
                        recommendation="Generate and submit an XML sitemap at /sitemap.xml.",
                        impact_score=5,
                    )
            except requests.RequestException:
                pass

            # ── Robots.txt ──
            try:
                robots_resp = requests.head(f"{url}/robots.txt", timeout=10)
                if robots_resp.status_code != 200:
                    score -= 3
                    AuditIssue.objects.create(
                        audit=audit, category="seo", severity="info",
                        title="No robots.txt found",
                        description="Robots.txt tells search engines which pages to crawl and which to skip.",
                        recommendation="Create a robots.txt file with appropriate directives.",
                        impact_score=3,
                    )
            except requests.RequestException:
                pass

            # ── Open Graph Tags ──
            og_title = soup.find("meta", attrs={"property": "og:title"})
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            og_image = soup.find("meta", attrs={"property": "og:image"})
            missing_og = []
            if not og_title:
                missing_og.append("og:title")
            if not og_desc:
                missing_og.append("og:description")
            if not og_image:
                missing_og.append("og:image")
            if missing_og:
                score -= 3
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="info",
                    title=f"Missing Open Graph tags: {', '.join(missing_og)}",
                    description="Open Graph tags control how your page appears when shared on social media.",
                    recommendation="Add og:title, og:description, and og:image meta tags for better social sharing.",
                    impact_score=3,
                )

            # ── Internal Links ──
            links = soup.find_all("a", href=True)
            internal = [a for a in links if a["href"].startswith("/") or a["href"].startswith(url)]
            if len(internal) < 3:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="seo", severity="warning",
                    title=f"Too few internal links ({len(internal)} found)",
                    description="Internal links help search engines discover and rank your pages.",
                    recommendation="Add contextual internal links to other important pages on your site.",
                    impact_score=5,
                )

        except requests.RequestException as e:
            logger.error(f"SEO analysis failed for {website.url}: {e}")
            score = 0
            AuditIssue.objects.create(
                audit=audit, category="seo", severity="critical",
                title="Could not reach website",
                description=f"Failed to fetch {website.url}: {str(e)[:200]}",
                recommendation="Ensure your website is accessible and the URL is correct.",
                impact_score=25,
            )

        return {"score": max(0, min(100, score))}
