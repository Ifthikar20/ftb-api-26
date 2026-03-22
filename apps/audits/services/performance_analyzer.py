import logging
import time

import requests
from bs4 import BeautifulSoup

from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class PerformanceAnalyzer:
    """Performance analysis: TTFB, page size, compression, render-blocking, images."""

    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        score = 100
        try:
            # Measure TTFB
            start = time.monotonic()
            response = requests.get(website.url, timeout=30, headers={
                "User-Agent": "FetchBot-Audit/1.0 (Performance Analyzer)"
            })
            ttfb_ms = (time.monotonic() - start) * 1000
            content = response.text
            soup = BeautifulSoup(content, "html.parser")
            headers = response.headers

            # ── Time to First Byte ──
            if ttfb_ms > 2000:
                score -= 20
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="critical",
                    title=f"Very slow TTFB: {ttfb_ms:.0f}ms",
                    description=f"Time to First Byte is {ttfb_ms:.0f}ms. Google recommends under 200ms, acceptable up to 600ms.",
                    recommendation="Use server-side caching, a CDN (Cloudflare, Fastly), optimize database queries, or upgrade hosting.",
                    impact_score=20,
                )
            elif ttfb_ms > 800:
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title=f"Slow TTFB: {ttfb_ms:.0f}ms",
                    description=f"TTFB is {ttfb_ms:.0f}ms. Target is under 600ms for good user experience.",
                    recommendation="Implement server caching, consider a CDN, and optimize backend response time.",
                    impact_score=10,
                )

            # ── Page Size ──
            page_size_kb = len(response.content) / 1024
            if page_size_kb > 5000:
                score -= 20
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="critical",
                    title=f"Very large page: {page_size_kb:.0f}KB",
                    description=f"Page is {page_size_kb:.0f}KB ({page_size_kb/1024:.1f}MB). Target is under 1.5MB.",
                    recommendation="Compress images to WebP/AVIF, minify CSS/JS, remove unused code, enable lazy loading.",
                    impact_score=20,
                )
            elif page_size_kb > 2000:
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title=f"Large page: {page_size_kb:.0f}KB",
                    description=f"Page is {page_size_kb:.0f}KB. Smaller pages load faster, especially on mobile.",
                    recommendation="Optimize images, minify CSS/JS, lazy load below-the-fold content.",
                    impact_score=10,
                )

            # ── Compression ──
            encoding = headers.get("Content-Encoding", "").lower()
            if "gzip" not in encoding and "br" not in encoding and "deflate" not in encoding:
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title="No compression enabled (gzip/brotli)",
                    description="Response is not compressed. Compression typically reduces transfer size by 60-80%.",
                    recommendation="Enable gzip or brotli compression on your web server (nginx, Apache, or CDN).",
                    impact_score=10,
                )

            # ── Render-Blocking Resources ──
            blocking_css = soup.find_all("link", attrs={"rel": "stylesheet"})
            blocking_js = [s for s in soup.find_all("script", src=True) if not s.get("async") and not s.get("defer")]
            if len(blocking_css) > 5:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title=f"{len(blocking_css)} render-blocking CSS files",
                    description="Each CSS file blocks page rendering until fully downloaded and parsed.",
                    recommendation="Combine CSS files, inline critical CSS, and defer non-critical stylesheets.",
                    impact_score=5,
                )
            if len(blocking_js) > 3:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title=f"{len(blocking_js)} render-blocking JavaScript files",
                    description="Synchronous scripts block HTML parsing and delay page rendering.",
                    recommendation="Add 'async' or 'defer' attributes to non-critical script tags.",
                    impact_score=5,
                    element=str(blocking_js[0])[:200] if blocking_js else "",
                )

            # ── Image Optimization ──
            images = soup.find_all("img", src=True)
            large_images = []
            unoptimized = []
            for img in images[:10]:  # Check first 10 images
                src = img.get("src", "")
                if src.endswith((".bmp", ".tiff")):
                    unoptimized.append(src)
                if not img.get("loading") == "lazy":
                    large_images.append(src)
                if not img.get("width") and not img.get("height"):
                    pass  # CLS check below

            if unoptimized:
                score -= 8
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title=f"{len(unoptimized)} images in unoptimized format",
                    description="BMP/TIFF images are very large. Modern formats are 5-10x smaller.",
                    recommendation="Convert images to WebP or AVIF format for 25-80% size reduction.",
                    impact_score=8,
                )

            # ── Lazy Loading ──
            below_fold_images = images[3:]  # Assuming first 3 are above fold
            not_lazy = [img for img in below_fold_images if img.get("loading") != "lazy"]
            if len(not_lazy) > 3:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="info",
                    title=f"{len(not_lazy)} images missing lazy loading",
                    description="Images below the fold should use lazy loading to speed up initial page load.",
                    recommendation='Add loading="lazy" to images not visible on initial load.',
                    impact_score=5,
                )

            # ── CLS (Cumulative Layout Shift) — image dimensions ──
            no_dimensions = [img for img in images if not img.get("width") and not img.get("height") and not img.get("style")]
            if len(no_dimensions) > 2:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="warning",
                    title=f"{len(no_dimensions)} images missing width/height (CLS risk)",
                    description="Images without dimensions cause layout shifts when they load, hurting Core Web Vitals CLS score.",
                    recommendation="Add explicit width and height attributes to all img tags.",
                    impact_score=5,
                )

            # ── Caching Headers ──
            cache_control = headers.get("Cache-Control", "")
            if not cache_control or "no-cache" in cache_control:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="performance", severity="info",
                    title="No browser caching configured",
                    description="Without cache headers, browsers re-download assets on every visit.",
                    recommendation="Set Cache-Control headers with appropriate max-age for static assets.",
                    impact_score=5,
                )

        except requests.RequestException as e:
            logger.error(f"Performance analysis failed for {website.url}: {e}")
            score = 0

        return {"score": max(0, min(100, score))}
