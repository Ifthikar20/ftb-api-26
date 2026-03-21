import logging
import requests
from bs4 import BeautifulSoup
from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class MobileAnalyzer:
    """Mobile-friendliness analysis: viewport, responsive, touch targets, font sizes."""

    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        score = 100
        try:
            response = requests.get(website.url, timeout=20, headers={
                "User-Agent": "FetchBot-Audit/1.0 (Mobile Analyzer)"
            })
            soup = BeautifulSoup(response.text, "html.parser")

            # ── Viewport Meta Tag ──
            viewport = soup.find("meta", attrs={"name": "viewport"})
            if not viewport:
                score -= 25
                AuditIssue.objects.create(
                    audit=audit, category="mobile", severity="critical",
                    title="Missing viewport meta tag",
                    description="Without a viewport tag, pages won't render properly on mobile devices.",
                    recommendation='Add <meta name="viewport" content="width=device-width, initial-scale=1"> to your <head>.',
                    impact_score=25,
                )
            elif viewport:
                content = viewport.get("content", "")
                if "width=device-width" not in content:
                    score -= 10
                    AuditIssue.objects.create(
                        audit=audit, category="mobile", severity="warning",
                        title="Viewport not set to device-width",
                        description=f"Viewport is '{content}' but should include 'width=device-width'.",
                        recommendation='Set viewport to width=device-width, initial-scale=1.',
                        impact_score=10,
                    )
                if "user-scalable=no" in content or "maximum-scale=1" in content:
                    score -= 5
                    AuditIssue.objects.create(
                        audit=audit, category="mobile", severity="warning",
                        title="Zoom disabled on mobile",
                        description="Preventing users from zooming is an accessibility violation.",
                        recommendation="Remove user-scalable=no and maximum-scale=1 from viewport meta.",
                        impact_score=5,
                    )

            # ── Responsive Design Indicators ──
            styles = soup.find_all("style")
            linked_css = soup.find_all("link", attrs={"rel": "stylesheet"})
            style_text = " ".join(s.string or "" for s in styles)
            has_media_queries = "@media" in style_text
            has_responsive_css = any("responsive" in (s.get("href") or "").lower() for s in linked_css)
            if not has_media_queries and not has_responsive_css and not linked_css:
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="mobile", severity="warning",
                    title="No responsive CSS detected",
                    description="No @media queries or responsive stylesheets found inline.",
                    recommendation="Use CSS media queries to adapt layout for different screen sizes.",
                    impact_score=10,
                )

            # ── Touch Targets ──
            small_buttons = []
            for el in soup.find_all(["a", "button", "input"]):
                style = el.get("style", "")
                # Check for very small explicit sizes
                if "font-size:" in style:
                    import re
                    sizes = re.findall(r"font-size:\s*(\d+)", style)
                    if sizes and int(sizes[0]) < 10:
                        small_buttons.append(str(el)[:100])
            if small_buttons:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="mobile", severity="info",
                    title=f"{len(small_buttons)} potentially small touch targets",
                    description="Interactive elements with very small font sizes may be hard to tap on mobile.",
                    recommendation="Ensure touch targets are at least 44x44px and have adequate spacing.",
                    impact_score=5,
                )

            # ── Fixed-Width Elements ──
            for el in soup.find_all(style=True):
                style = el.get("style", "")
                if "width:" in style and "px" in style and "max-width" not in style:
                    import re
                    widths = re.findall(r"width:\s*(\d+)px", style)
                    if widths and int(widths[0]) > 500:
                        score -= 8
                        AuditIssue.objects.create(
                            audit=audit, category="mobile", severity="warning",
                            title="Fixed-width element may cause horizontal scrolling",
                            description=f"Element with width: {widths[0]}px could overflow on mobile screens.",
                            recommendation="Use percentage widths, max-width, or CSS flexbox/grid for responsive layouts.",
                            impact_score=8, element=str(el)[:200],
                        )
                        break

            # ── Text Readability ──
            text_elements = soup.find_all(["p", "li", "td", "span"])
            for el in text_elements[:5]:
                style = el.get("style", "")
                if "font-size:" in style:
                    import re
                    sizes = re.findall(r"font-size:\s*(\d+)", style)
                    if sizes and int(sizes[0]) < 12:
                        score -= 5
                        AuditIssue.objects.create(
                            audit=audit, category="mobile", severity="info",
                            title="Text too small for mobile",
                            description=f"Found text with font-size: {sizes[0]}px. Minimum recommended is 16px.",
                            recommendation="Use at least 16px font size for body text on mobile devices.",
                            impact_score=5,
                        )
                        break

            # ── Tap-Friendly Links ──
            links = soup.find_all("a")
            close_links = 0
            for i, link in enumerate(links[:20]):
                if link.string and len(link.string.strip()) < 3:
                    close_links += 1
            if close_links > 3:
                score -= 3
                AuditIssue.objects.create(
                    audit=audit, category="mobile", severity="info",
                    title=f"{close_links} links with very short text",
                    description="Short link text (1-2 chars) makes links hard to tap on mobile.",
                    recommendation="Use descriptive link text that's easy to tap on touchscreens.",
                    impact_score=3,
                )

        except requests.RequestException as e:
            logger.error(f"Mobile analysis failed for {website.url}: {e}")
            score = 0

        return {"score": max(0, min(100, score))}
