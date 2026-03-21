import logging
import re
import requests
from bs4 import BeautifulSoup
from apps.audits.models import Audit, AuditIssue

logger = logging.getLogger("apps")


class ContentAnalyzer:
    """Content quality analysis: word count, readability, headings, broken links, freshness."""

    @staticmethod
    def analyze(*, website, audit: Audit) -> dict:
        score = 100
        try:
            response = requests.get(website.url, timeout=20, headers={
                "User-Agent": "FetchBot-Audit/1.0 (Content Analyzer)"
            })
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script/style elements for text analysis
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            words = text.split()
            word_count = len(words)

            # ── Word Count (Thin Content) ──
            if word_count < 100:
                score -= 20
                AuditIssue.objects.create(
                    audit=audit, category="content", severity="critical",
                    title=f"Very thin content: only {word_count} words",
                    description="Pages with less than 100 words are considered 'thin' by Google and rarely rank well.",
                    recommendation="Add substantive content — aim for at least 300-500 words of unique, valuable content.",
                    impact_score=20,
                )
            elif word_count < 300:
                score -= 10
                AuditIssue.objects.create(
                    audit=audit, category="content", severity="warning",
                    title=f"Low content: {word_count} words",
                    description="Pages with under 300 words may struggle to rank for competitive queries.",
                    recommendation="Expand your content to 500-1000+ words with useful, in-depth information.",
                    impact_score=10,
                )

            # ── Readability (Flesch-Kincaid approximation) ──
            if word_count > 50:
                sentences = re.split(r'[.!?]+', text)
                sentence_count = max(1, len([s for s in sentences if s.strip()]))
                syllable_count = sum(ContentAnalyzer._count_syllables(w) for w in words[:200])
                avg_words_per_sentence = word_count / sentence_count
                avg_syllables_per_word = syllable_count / min(word_count, 200)

                # Simplified Flesch Reading Ease
                reading_ease = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
                reading_ease = max(0, min(100, reading_ease))

                if reading_ease < 30:
                    score -= 10
                    AuditIssue.objects.create(
                        audit=audit, category="content", severity="warning",
                        title=f"Content is very difficult to read (Flesch score: {reading_ease:.0f})",
                        description="Reading ease below 30 means content is college-level difficulty. Most web content should target 60-70.",
                        recommendation="Use shorter sentences, simpler words, and break up long paragraphs.",
                        impact_score=10,
                    )
                elif reading_ease < 50:
                    score -= 5
                    AuditIssue.objects.create(
                        audit=audit, category="content", severity="info",
                        title=f"Content could be more readable (Flesch score: {reading_ease:.0f})",
                        description="A reading ease of 50-60 is acceptable but could be improved for wider audience reach.",
                        recommendation="Simplify language where possible. Target a Flesch score of 60-70.",
                        impact_score=5,
                    )

            # ── Heading Structure ──
            headings = soup.find_all(re.compile(r'^h[1-6]$'))
            if not headings:
                score -= 8
                AuditIssue.objects.create(
                    audit=audit, category="content", severity="warning",
                    title="No headings found",
                    description="Content without headings is harder to scan and less accessible.",
                    recommendation="Structure your content with H1, H2, and H3 headings.",
                    impact_score=8,
                )
            elif word_count > 500 and len(headings) < 3:
                score -= 5
                AuditIssue.objects.create(
                    audit=audit, category="content", severity="info",
                    title=f"Too few headings for content length ({len(headings)} headings for {word_count} words)",
                    description="Long content should be broken into scannable sections with sub-headings.",
                    recommendation="Add H2/H3 headings every 150-300 words to improve readability.",
                    impact_score=5,
                )

            # ── Broken Internal Links ──
            links = soup.find_all("a", href=True)
            url_base = website.url.rstrip("/")
            broken = []
            checked = 0
            for link in links[:15]:  # Check first 15 links
                href = link["href"]
                if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
                    continue
                if href.startswith("/"):
                    href = url_base + href
                if not href.startswith("http"):
                    continue
                try:
                    r = requests.head(href, timeout=5, allow_redirects=True)
                    checked += 1
                    if r.status_code >= 400:
                        broken.append({"url": href, "status": r.status_code})
                except requests.RequestException:
                    broken.append({"url": href, "status": "timeout"})
                    checked += 1
            if broken:
                penalty = min(15, len(broken) * 5)
                score -= penalty
                AuditIssue.objects.create(
                    audit=audit, category="content", severity="critical" if len(broken) >= 3 else "warning",
                    title=f"{len(broken)} broken link(s) detected",
                    description=f"Found {len(broken)} links returning errors: " + ", ".join(f"{b['url']} ({b['status']})" for b in broken[:3]),
                    recommendation="Fix or remove broken links. Broken links hurt SEO and user experience.",
                    impact_score=penalty,
                    element=broken[0]["url"] if broken else "",
                )

            # ── Duplicate Content Indicators ──
            paragraphs = soup.find_all("p")
            p_texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
            if p_texts:
                seen = set()
                dupes = 0
                for text_p in p_texts:
                    if len(text_p) > 30:
                        if text_p in seen:
                            dupes += 1
                        seen.add(text_p)
                if dupes > 2:
                    score -= 8
                    AuditIssue.objects.create(
                        audit=audit, category="content", severity="warning",
                        title=f"{dupes} duplicate text blocks found",
                        description="Repeated content on the same page dilutes relevance and can confuse search engines.",
                        recommendation="Remove or consolidate duplicate text blocks.",
                        impact_score=8,
                    )

            # ── Last Modified / Content Freshness ──
            last_modified = response.headers.get("Last-Modified")
            if last_modified:
                from datetime import datetime
                try:
                    mod_date = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
                    days_old = (datetime.utcnow() - mod_date).days
                    if days_old > 365:
                        score -= 5
                        AuditIssue.objects.create(
                            audit=audit, category="content", severity="info",
                            title=f"Content last modified {days_old} days ago",
                            description="Search engines prefer fresh content. This page hasn't been updated in over a year.",
                            recommendation="Review and update your content regularly. Even small updates signal freshness.",
                            impact_score=5,
                        )
                except ValueError:
                    pass

        except requests.RequestException as e:
            logger.error(f"Content analysis failed for {website.url}: {e}")
            score = 0

        return {"score": max(0, min(100, score))}

    @staticmethod
    def _count_syllables(word):
        """Approximate syllable count for readability calculation."""
        word = word.lower().strip(".,!?;:'\"")
        if len(word) <= 3:
            return 1
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e"):
            count -= 1
        return max(1, count)
