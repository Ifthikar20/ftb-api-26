"""
Onboarding orchestrator.

Single entry point for the post-register flow: take a URL, return
everything we know about the business so the user only has to confirm
or tweak rather than type from scratch.

Composes three existing services:
    1. ``apps.llm_ranking.services.domain_scanner.scan_domain``
       — homepage scrape, products / features / selling points / topics
    2. ``apps.onboarding.services.description_writer.polish_description``
       — short Claude pass that rewrites the meta description into the
       1-2 sentence "what we do" copy the user actually wants to see
    3. ``apps.llm_ranking.services.competitor_discovery.discover_competitors``
       — Google-Search-backed real competitor list

All three are best-effort. A failure in any one returns a degraded
result rather than aborting; the frontend renders whatever fields came
back so the user can fill the rest by hand.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger("apps")


@dataclass
class OnboardingPayload:
    """What we hand back to the wizard so it can render Step 2 + 3."""

    url: str
    success: bool = False
    error: str | None = None

    # Identity
    business_name: str = ""
    domain: str = ""
    industry: str = ""

    # Description: ``description_short`` is the 1-2 sentence polished
    # version intended for display. ``description_raw`` is whatever the
    # scraper extracted from meta tags / og:description.
    description_short: str = ""
    description_raw: str = ""

    # Inventory derived from the homepage
    products: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    selling_points: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    # Discovered competitors {name, domain}
    competitors: list[dict] = field(default_factory=list)


def run_onboarding_scan(url: str) -> OnboardingPayload:
    """Scan + polish + discover, returning a single payload for the UI."""
    from apps.llm_ranking.services.domain_scanner import scan_domain

    payload = OnboardingPayload(url=url)

    scan = scan_domain(url)
    if not scan.get("success"):
        payload.error = scan.get("error") or "Could not scan this domain."
        return payload

    payload.success = True
    payload.business_name = scan.get("business_name") or ""
    payload.industry = scan.get("industry") or ""
    payload.domain = scan.get("domain") or _domain_of(url)
    payload.description_raw = scan.get("description") or ""
    payload.products = list(scan.get("products") or [])[:8]
    payload.features = list(scan.get("features") or [])[:8]
    payload.selling_points = list(scan.get("selling_points") or [])[:6]
    payload.topics = list(scan.get("topics") or [])[:10]

    payload.description_short = _polish_description(
        business_name=payload.business_name,
        industry=payload.industry,
        raw_description=payload.description_raw,
        selling_points=payload.selling_points,
        products=payload.products,
    )

    # Replace the heuristic topic list with an LLM-generated one. The
    # heuristic generator hardcodes the word "tools" and regex-matches
    # fragments around "for", producing nonsense topics for non-product
    # businesses (services, agencies, healthcare, finance). The LLM
    # picks the right category noun on its own.
    llm_topics = _llm_topics(
        business_name=payload.business_name,
        industry=payload.industry,
        description=payload.description_short or payload.description_raw,
        selling_points=payload.selling_points,
        products=payload.products,
    )
    if llm_topics:
        payload.topics = llm_topics

    payload.competitors = _safe_discover_competitors(
        business_name=payload.business_name,
        industry=payload.industry,
        domain=payload.domain,
        description=payload.description_short or payload.description_raw,
    )

    return payload


def _domain_of(url: str) -> str:
    try:
        return urlparse(url if url.startswith("http") else f"https://{url}").netloc
    except Exception:
        return ""


def _polish_description(
    *,
    business_name: str,
    industry: str,
    raw_description: str,
    selling_points: list[str],
    products: list[str],
) -> str:
    """
    Ask Claude Haiku for a clean 1-2 sentence "what they do" line.

    Falls back to the scraped meta description (truncated) when the LLM
    call isn't available.
    """
    fallback = (raw_description or "").strip()
    if len(fallback) > 280:
        fallback = fallback[:277].rsplit(" ", 1)[0] + "…"

    try:
        from django.conf import settings as dj_settings
        api_key = getattr(dj_settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return fallback

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        bullets = ""
        if selling_points:
            bullets += "\nSelling points:\n- " + "\n- ".join(selling_points[:5])
        if products:
            bullets += "\nProducts:\n- " + "\n- ".join(products[:5])

        prompt = (
            f"Write a clean 1-2 sentence description (max 200 chars) of "
            f"what this business does. Use plain language, no marketing fluff.\n\n"
            f"Business: {business_name}\n"
            f"Industry: {industry}\n"
            f"Existing description: {raw_description}{bullets}\n\n"
            f"Return only the description, no preamble."
        )
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.content[0].text or "").strip().strip('"')
        # Track usage so the same dashboard-level cost roll-up captures it.
        try:
            from core.ai_tracking import record_usage
            record_usage(
                module="onboarding",
                model_name="claude-haiku-4-5",
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                metadata={"role": "description_polish"},
            )
        except Exception:
            pass
        return text or fallback
    except Exception as exc:
        logger.debug("Description polish skipped: %s", exc)
        return fallback


def _llm_topics(
    *,
    business_name: str,
    industry: str,
    description: str,
    selling_points: list[str],
    products: list[str],
) -> list[str]:
    """
    Ask Claude Haiku for 8 buyer-intent search queries that actually
    match the business.

    Key requirement: the LLM picks the right category noun based on what
    this business is — "service" / "provider" / "platform" / "solution"
    / "agency" / "tools" — instead of the heuristic generator's
    hardcoded "tools" suffix. The description is the primary input so
    topics correlate with what the user just confirmed.

    Returns [] on failure so the caller can fall back to the heuristic
    list rather than ending up with an empty topic field.
    """
    if not (business_name or description):
        return []
    try:
        from django.conf import settings as dj_settings
        api_key = getattr(dj_settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return []

        import anthropic
        import json
        import re

        client = anthropic.Anthropic(api_key=api_key)

        bullets = ""
        if selling_points:
            bullets += "\nKey selling points:\n- " + "\n- ".join(selling_points[:5])
        if products:
            bullets += "\nProducts / services offered:\n- " + "\n- ".join(products[:5])

        prompt = (
            "You are generating buyer-intent search queries that real "
            "people would type into ChatGPT, Claude, or Perplexity when "
            "looking for a business like this one.\n\n"
            f"Business: {business_name}\n"
            f"Industry: {industry or 'unspecified'}\n"
            f"Description: {description}{bullets}\n\n"
            "Return 8 queries that satisfy ALL of:\n"
            "1. Each query reads as a natural sentence a human would "
            "actually type — no fragment soup, no broken grammar.\n"
            "2. Pick the right category noun based on what this business "
            "IS. A SaaS product → 'tool' / 'platform' / 'software'. A "
            "credentialing service or agency → 'service' / 'provider' / "
            "'company'. A consultancy → 'firm' / 'consultant'. Match the "
            "noun to the business; do not blindly say 'tools' for a "
            "non-software business.\n"
            "3. Each query must be correlated with the description above "
            "— if the description mentions 'provider credentialing for "
            "medical practices', the queries should be about provider "
            "credentialing for medical practices, not generic.\n"
            "4. Mix query styles: 'best X for Y', 'how to find Z', "
            "'top alternatives to ...', 'who handles ...', 'compare ...'.\n"
            "5. Each query is 4-12 words. No trailing punctuation.\n\n"
            "Return ONLY a JSON array of 8 strings. No prose, no keys, no "
            "code fences. Example output:\n"
            '["best provider credentialing services for small clinics", '
            '"how to get doctors in-network fast"]'
        )

        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.content[0].text or "").strip()

        try:
            from core.ai_tracking import record_usage
            record_usage(
                module="onboarding",
                model_name="claude-haiku-4-5",
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                metadata={"role": "topic_generation"},
            )
        except Exception:
            pass

        # Extract the first JSON array in the response — robust to the
        # occasional model preamble or trailing fence.
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group())
        if not isinstance(data, list):
            return []
        topics = [t.strip().rstrip(".,") for t in data if isinstance(t, str)]
        # Light sanity: drop empties, dedupe, cap to 8.
        seen = set()
        out: list[str] = []
        for t in topics:
            key = t.lower()
            if len(t) < 6 or key in seen:
                continue
            seen.add(key)
            out.append(t)
            if len(out) >= 8:
                break
        return out
    except Exception as exc:
        logger.debug("LLM topic generation skipped: %s", exc)
        return []


def _llm_competitors(
    *,
    business_name: str,
    industry: str,
    domain: str,
    description: str,
) -> list[dict]:
    """
    Ask Claude Haiku to name 8 real competitors of the business.

    Replaces (or precedes, depending on availability) the Google
    Custom Search competitor discoverer. Google closed Custom Search
    JSON API to new customers in early 2026, so this path is the
    primary source for newly-provisioned tenants; Google is used as
    an optional fallback when an existing tenant still has a working
    key.

    The LLM is well-suited to this task — it doesn't need to "search"
    for Stripe's competitors; it already knows them. Returns
    [{"name", "domain"}, ...] in the same shape the wizard expects.
    """
    if not (business_name or description):
        return []
    try:
        from django.conf import settings as dj_settings
        api_key = getattr(dj_settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return []

        import anthropic
        import json
        import re

        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            "Name real, currently-operating companies that directly "
            "compete with the business below. Only include companies "
            "you are reasonably sure exist — do not invent names.\n\n"
            f"Business: {business_name}\n"
            f"Industry: {industry or 'unspecified'}\n"
            f"Website: {domain or 'unknown'}\n"
            f"Description: {description}\n\n"
            "Return 6-8 competitors. For each, give the public-facing "
            "company name and the primary website domain (e.g. "
            "'stripe.com', not 'https://stripe.com/'). Exclude the "
            "subject company itself from the list.\n\n"
            "Return ONLY a JSON array of objects, no prose, no code "
            "fences. Example:\n"
            '[{"name": "Stripe", "domain": "stripe.com"}, '
            '{"name": "Adyen", "domain": "adyen.com"}]'
        )

        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.content[0].text or "").strip()

        try:
            from core.ai_tracking import record_usage
            record_usage(
                module="onboarding",
                model_name="claude-haiku-4-5",
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                metadata={"role": "competitor_discovery"},
            )
        except Exception:
            pass

        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        data = json.loads(match.group())
        if not isinstance(data, list):
            return []

        # Normalise + dedupe. Drop entries that don't at least have a
        # name; strip protocol from domain just in case.
        own = (domain or "").lower().lstrip("www.")
        seen: set[str] = set()
        out: list[dict] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            name = (row.get("name") or "").strip()
            if not name:
                continue
            comp_domain = (row.get("domain") or "").strip().lower()
            comp_domain = re.sub(r"^https?://", "", comp_domain).rstrip("/")
            comp_domain = comp_domain.lstrip("www.")
            if comp_domain and comp_domain == own:
                continue  # skip self
            key = comp_domain or name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"name": name, "domain": comp_domain})
            if len(out) >= 8:
                break
        return out
    except Exception as exc:
        logger.debug("LLM competitor discovery skipped: %s", exc)
        return []


def _safe_discover_competitors(
    *, business_name: str, industry: str, domain: str, description: str,
) -> list[dict]:
    """
    Find competitors for the onboarded website.

    Order:
        1. LLM (Claude Haiku) — primary path, works without third-party APIs.
        2. Google Custom Search — optional fallback for legacy tenants that
           still have a working key (Google closed it to new customers).

    Returns [] if everything fails so the wizard renders the empty
    state rather than aborting.
    """
    if not (business_name or industry):
        return []

    # Primary: LLM
    competitors = _llm_competitors(
        business_name=business_name,
        industry=industry,
        domain=domain,
        description=description,
    )
    if competitors:
        return competitors

    # Fallback: Google Custom Search (only useful for tenants still
    # within the legacy CSE window).
    try:
        from apps.llm_ranking.services.competitor_discovery import discover_competitors
        return discover_competitors(
            business_name=business_name,
            industry=industry,
            domain=domain,
            description=description,
            max_results=8,
        ) or []
    except Exception as exc:
        logger.debug("Google competitor discovery skipped: %s", exc)
        return []


def to_dict(payload: OnboardingPayload) -> dict:
    return asdict(payload)
