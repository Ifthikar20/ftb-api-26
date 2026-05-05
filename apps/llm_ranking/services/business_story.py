"""
Business Story builder.

Before each audit runs, we want a richer picture of the business than
the basic ``domain_scanner.scan_domain`` produces. This service:

  1. Re-fetches the homepage and pulls structured data the basic
     scanner ignores: JSON-LD blocks (schema.org), Open Graph + Twitter
     card tags, FAQ + Review + Product schemas, contact info, social
     links, pricing strings, and tech-stack hints.

  2. Composes a markdown "business story" — a single self-contained
     blob that Claude can read as ground truth about who the business
     is, what it sells, what it costs, what reviewers say, and how
     competitors describe themselves.

  3. Hands the story to the RAG ingest pipeline so subsequent audit
     cells can retrieve relevant facts per prompt.

The whole module degrades gracefully — if the homepage 404s, JSON
parsing fails, or the LLM polish hits a 401, the audit continues
with whatever partial context we managed to gather.
"""
from __future__ import annotations

import json
import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger("apps")


# Maximum characters of "business story" we hand to the RAG ingest.
# 16KB is plenty for a homepage's worth of structured data and keeps
# the embedded chunk count reasonable.
_MAX_STORY_CHARS = 16_000


# ── HTML parser specialised for structured-data extraction ──────────────


class _StructuredDataExtractor(HTMLParser):
    """
    Pulls JSON-LD blocks, OG / Twitter cards, FAQ summary text, and
    social/contact links from a homepage. Strictly read-only.
    """

    _SOCIAL_HOSTS = (
        "twitter.com", "x.com", "linkedin.com", "facebook.com",
        "instagram.com", "github.com", "youtube.com", "tiktok.com",
        "discord.gg", "discord.com", "reddit.com",
    )

    def __init__(self) -> None:
        super().__init__()
        self.json_ld_blocks: list[str] = []
        self.og: dict[str, str] = {}
        self.twitter: dict[str, str] = {}
        self.canonical: str = ""
        self.author: str = ""
        self.generator: str = ""
        self.theme_color: str = ""
        self.contact_emails: set[str] = set()
        self.contact_phones: set[str] = set()
        self.social_links: set[str] = set()
        self.pricing_snippets: list[str] = []
        self.faq_pairs: list[tuple[str, str]] = []
        # Internal parser state
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []
        self._in_text_capture = False
        self._text_buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "script" and (attrs_d.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buf = []
        elif tag == "meta":
            self._read_meta(attrs_d)
        elif tag == "link":
            rel = (attrs_d.get("rel") or "").lower()
            href = attrs_d.get("href", "")
            if rel == "canonical" and href:
                self.canonical = href
        elif tag == "a":
            href = attrs_d.get("href", "")
            self._capture_link(href)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            blob = "".join(self._jsonld_buf).strip()
            if blob:
                self.json_ld_blocks.append(blob)
            self._jsonld_buf = []

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_buf.append(data)
            return
        # Look for pricing markers in any text node. Keep the snippet
        # narrow — 60 chars on either side of the price.
        if "$" in data or "/mo" in data.lower() or "/month" in data.lower():
            for m in re.finditer(
                r"\$[\d,]+(?:\.\d{1,2})?(?:\s*/\s*(?:mo|month|user|yr|year))?",
                data,
            ):
                snippet = data[max(0, m.start() - 60): m.end() + 60].strip()
                if 3 <= len(snippet) <= 200:
                    self.pricing_snippets.append(snippet)

    def _read_meta(self, attrs_d: dict) -> None:
        name = (attrs_d.get("name") or "").lower()
        prop = (attrs_d.get("property") or "").lower()
        content = attrs_d.get("content") or ""
        if not content:
            return
        if prop.startswith("og:"):
            self.og[prop[3:]] = content[:500]
        elif name.startswith("twitter:"):
            self.twitter[name[len("twitter:"):]] = content[:500]
        elif name == "author":
            self.author = content[:200]
        elif name == "generator":
            self.generator = content[:200]
        elif name == "theme-color":
            self.theme_color = content[:50]

    def _capture_link(self, href: str) -> None:
        if not href:
            return
        href_lower = href.lower()
        if href_lower.startswith("mailto:"):
            email = href[7:].split("?")[0].strip()
            if email and "@" in email:
                self.contact_emails.add(email[:200])
            return
        if href_lower.startswith("tel:"):
            phone = href[4:].split("?")[0].strip()
            if phone:
                self.contact_phones.add(phone[:50])
            return
        for host in self._SOCIAL_HOSTS:
            if host in href_lower:
                self.social_links.add(href[:300])
                return


# ── JSON-LD interpretation ─────────────────────────────────────────────


def _parse_jsonld(blocks: list[str]) -> dict:
    """
    Walk every JSON-LD blob and extract the schema.org @types we care
    about. Returns a compact dict the renderer can iterate over.
    """
    out: dict = {
        "organization": [],
        "products": [],
        "offers": [],
        "faq": [],
        "reviews": [],
        "rating": None,
    }
    for raw in blocks:
        try:
            data = json.loads(raw)
        except Exception:
            continue
        # @graph wraps multiple items
        items = data.get("@graph") if isinstance(data, dict) else None
        if items is None:
            items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type") or ""
            if isinstance(t, list):
                t = next(iter(t), "")
            t = str(t)
            if t in ("Organization", "LocalBusiness", "Corporation"):
                out["organization"].append({
                    "name": item.get("name", "")[:200],
                    "description": (item.get("description") or "")[:400],
                    "url": item.get("url", ""),
                    "logo": _coerce_url(item.get("logo")),
                    "sameAs": item.get("sameAs") or [],
                })
            elif t in ("Product", "Service", "SoftwareApplication"):
                offers = item.get("offers") or []
                if isinstance(offers, dict):
                    offers = [offers]
                out["products"].append({
                    "name": item.get("name", "")[:200],
                    "description": (item.get("description") or "")[:400],
                    "category": item.get("category", ""),
                    "offers": [_strip_offer(o) for o in offers if isinstance(o, dict)][:4],
                })
            elif t == "Offer":
                out["offers"].append(_strip_offer(item))
            elif t in ("FAQPage", "Question"):
                for q in item.get("mainEntity") or [item]:
                    if not isinstance(q, dict):
                        continue
                    name = (q.get("name") or "").strip()
                    answer = q.get("acceptedAnswer") or {}
                    if isinstance(answer, dict):
                        answer_text = (answer.get("text") or "").strip()
                    else:
                        answer_text = ""
                    if name and answer_text:
                        out["faq"].append({"q": name[:300], "a": answer_text[:400]})
            elif t in ("Review", "AggregateRating"):
                if t == "AggregateRating":
                    out["rating"] = {
                        "value": item.get("ratingValue"),
                        "count": item.get("reviewCount") or item.get("ratingCount"),
                        "best": item.get("bestRating", 5),
                    }
                else:
                    body = (item.get("reviewBody") or "").strip()
                    rating = (item.get("reviewRating") or {})
                    if isinstance(rating, dict):
                        rating = rating.get("ratingValue", "")
                    if body:
                        out["reviews"].append({
                            "rating": rating, "body": body[:300],
                            "author": _coerce_name(item.get("author")),
                        })
    # Cap each list — a hostile schema with 10K entries shouldn't blow
    # up the story.
    out["organization"] = out["organization"][:3]
    out["products"] = out["products"][:8]
    out["offers"] = out["offers"][:8]
    out["faq"] = out["faq"][:10]
    out["reviews"] = out["reviews"][:8]
    return out


def _strip_offer(offer: dict) -> dict:
    return {
        "price": offer.get("price"),
        "currency": offer.get("priceCurrency"),
        "availability": (offer.get("availability") or "").rsplit("/", 1)[-1],
        "name": (offer.get("name") or "")[:200],
    }


def _coerce_url(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("url", "") or value.get("@id", "") or ""
    return ""


def _coerce_name(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("name", "")
    return ""


# ── Public API ─────────────────────────────────────────────────────────


def gather_story(url: str) -> dict:
    """
    Fetch ``url`` and return a structured business-story dict suitable
    for ``render_story`` and downstream RAG ingestion.

    Always returns a dict (never raises). On failure the dict has
    ``error`` set; callers should use whatever fields are populated.
    """
    from core.validators.safe_http import FetchError, safe_get

    try:
        resp = safe_get(url, timeout=12, max_bytes=900_000)
    except FetchError as exc:
        return {"url": url, "error": str(exc)[:200]}
    html = resp.text or ""
    if resp.status_code >= 400:
        return {"url": url, "error": f"HTTP {resp.status_code}"}

    parser = _StructuredDataExtractor()
    try:
        parser.feed(html)
    except Exception as exc:
        logger.debug("HTML parse error for %s: %s", url, exc)

    structured = _parse_jsonld(parser.json_ld_blocks)

    return {
        "url": resp.final_url or url,
        "canonical": parser.canonical,
        "og": parser.og,
        "twitter": parser.twitter,
        "author": parser.author,
        "generator": parser.generator,
        "theme_color": parser.theme_color,
        "structured": structured,
        "contacts": {
            "emails": sorted(parser.contact_emails)[:5],
            "phones": sorted(parser.contact_phones)[:3],
        },
        "social_links": sorted(parser.social_links)[:10],
        "pricing_snippets": _dedupe_preserve_order(parser.pricing_snippets)[:8],
    }


def render_story(story: dict, *, business_name: str = "", industry: str = "") -> str:
    """
    Compose a markdown blob from a ``gather_story`` result. The blob
    is what goes into the RAG ingest — it has clear section headers
    so the chunker keeps related facts together.
    """
    lines: list[str] = []
    lines.append("=== BUSINESS STORY ===")
    if business_name:
        lines.append(f"Business: {business_name}")
    if industry:
        lines.append(f"Industry: {industry}")
    if story.get("error"):
        lines.append(f"(scraper error: {story['error']})")
        return _trim("\n".join(lines))

    og = story.get("og") or {}
    if og.get("title") or og.get("description"):
        lines.append("")
        lines.append("=== POSITIONING (Open Graph) ===")
        if og.get("title"):
            lines.append(f"Title: {og['title']}")
        if og.get("description"):
            lines.append(f"Description: {og['description']}")
        if og.get("site_name"):
            lines.append(f"Site name: {og['site_name']}")
        if og.get("type"):
            lines.append(f"Type: {og['type']}")

    twitter = story.get("twitter") or {}
    if twitter.get("description") and twitter.get("description") != og.get("description"):
        lines.append(f"Twitter pitch: {twitter['description']}")

    structured = story.get("structured") or {}

    org = structured.get("organization") or []
    if org:
        lines.append("")
        lines.append("=== ORGANIZATION (schema.org) ===")
        for o in org:
            if o.get("name"):
                lines.append(f"- {o['name']}")
            if o.get("description"):
                lines.append(f"  {o['description']}")
            if o.get("sameAs"):
                lines.append(f"  Linked profiles: {', '.join(o['sameAs'][:5])}")

    products = structured.get("products") or []
    if products:
        lines.append("")
        lines.append("=== PRODUCTS / SERVICES ===")
        for p in products:
            line = f"- {p.get('name', 'Unnamed product')}"
            if p.get("description"):
                line += f": {p['description']}"
            lines.append(line)
            for offer in p.get("offers") or []:
                price = offer.get("price")
                if price is not None:
                    lines.append(
                        f"  Offer: {offer.get('currency', '')} {price} "
                        f"({offer.get('availability', '')})"
                    )

    rating = structured.get("rating")
    if rating and rating.get("value") is not None:
        lines.append("")
        lines.append("=== REVIEWS / RATING ===")
        lines.append(
            f"Aggregate rating: {rating['value']} / {rating.get('best', 5)} "
            f"({rating.get('count', '?')} reviews)"
        )
    reviews = structured.get("reviews") or []
    if reviews:
        if not (rating and rating.get("value") is not None):
            lines.append("")
            lines.append("=== REVIEWS ===")
        for r in reviews:
            who = r.get("author") or "anon"
            stars = r.get("rating")
            tag = f"{stars}/5" if stars else ""
            lines.append(f'- {who} {tag}: "{r["body"]}"')

    faq = structured.get("faq") or []
    if faq:
        lines.append("")
        lines.append("=== FAQ ===")
        for entry in faq:
            lines.append(f"Q: {entry['q']}")
            lines.append(f"A: {entry['a']}")

    pricing = story.get("pricing_snippets") or []
    if pricing:
        lines.append("")
        lines.append("=== PRICING SIGNALS ===")
        for p in pricing:
            lines.append(f"- {p}")

    contacts = story.get("contacts") or {}
    socials = story.get("social_links") or []
    if contacts.get("emails") or contacts.get("phones") or socials:
        lines.append("")
        lines.append("=== CONTACT / SOCIAL ===")
        if contacts.get("emails"):
            lines.append(f"Emails: {', '.join(contacts['emails'])}")
        if contacts.get("phones"):
            lines.append(f"Phones: {', '.join(contacts['phones'])}")
        if socials:
            lines.append(f"Profiles: {', '.join(socials)}")

    if story.get("generator") or story.get("author"):
        lines.append("")
        lines.append("=== TECH / META ===")
        if story.get("generator"):
            lines.append(f"Generator: {story['generator']}")
        if story.get("author"):
            lines.append(f"Author: {story['author']}")

    return _trim("\n".join(lines))


def gather_and_ingest(*, url: str, audit, user, website) -> dict:
    """
    Fetch the site, render the business story, and ingest it into the
    user's RAG knowledge base under the audit's pseudo-URL. Returns
    the gathered story dict plus an ``ingest_status`` indicator.

    Best-effort: ingest failures are logged but don't propagate, so a
    misconfigured RAG never blocks an audit.
    """
    story = gather_story(url)
    rendered = render_story(
        story, business_name=audit.business_name, industry=audit.industry,
    )
    ingest_status = "skipped"
    if rendered.strip():
        try:
            from apps.rag.services.ingest_service import ingest_audit_context
            ingest_audit_context(
                user=user, website=website,
                audit_id=str(audit.id), llm_context=rendered,
            )
            ingest_status = "ok"
        except Exception as exc:
            logger.debug("Business-story RAG ingest failed: %s", exc)
            ingest_status = f"error: {str(exc)[:120]}"
    return {"story": story, "rendered": rendered, "ingest_status": ingest_status}


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _trim(text: str) -> str:
    return text[:_MAX_STORY_CHARS]
