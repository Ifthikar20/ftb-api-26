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


def _safe_discover_competitors(
    *, business_name: str, industry: str, domain: str, description: str,
) -> list[dict]:
    """Wrap the LLM-ranking discoverer so a failure doesn't abort onboarding."""
    if not (business_name or industry):
        return []
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
        logger.debug("Competitor discovery skipped: %s", exc)
        return []


def to_dict(payload: OnboardingPayload) -> dict:
    return asdict(payload)
