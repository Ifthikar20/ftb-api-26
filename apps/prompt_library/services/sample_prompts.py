"""Business-grounded sample-prompt generation.

The old sample generator substituted the website's industry into generic
templates and, when the industry was blank, defaulted it to the literal
string "software" — so a freshly-added car / finance / agency site got a
list of nonsense SaaS prompts.

This reads the site first (if it has not been classified yet), then asks
Claude for buyer-intent prompts written for what the business ACTUALLY
does, inferring the right category noun from the real description. It
falls back to the deterministic template library only with a REAL
industry, and never to a hardcoded "software" default.
"""
import json
import logging
import re

from core.llm import ClaudeUtility

logger = logging.getLogger("apps")


def _scan_and_persist(website) -> tuple[str, str, list[str]]:
    """Ensure the site has been read. Returns (industry, description, products).

    When the website already carries an industry and a description we trust
    them and skip the scan. Otherwise we scan the homepage and persist
    whatever we learn so future runs (and audits) reuse it.
    """
    industry = (website.industry or "").strip()
    description = (website.description or "").strip()
    if industry and description:
        return industry, description, []

    from apps.llm_ranking.services.domain_scanner import scan_domain

    try:
        scan = scan_domain(website.url)
    except Exception as exc:
        logger.warning("Sample-prompt scan failed for %s: %s", website.url, exc)
        return industry, description, []
    if not scan.get("success"):
        logger.info("Sample-prompt scan unsuccessful for %s", website.url)
        return industry, description, []

    new_industry = industry or (scan.get("industry") or "").strip()
    new_description = description or (scan.get("description") or "").strip()
    products = list(scan.get("products") or [])[:8]

    fields = []
    if new_industry and not industry:
        website.industry = new_industry[:100]
        fields.append("industry")
    if new_description and not description:
        website.description = new_description
        fields.append("description")
    if fields:
        try:
            website.save(update_fields=[*fields, "updated_at"])
        except Exception:
            website.save()

    return new_industry, new_description, products


def _llm_prompts(*, business_name, industry, description, products, count,
                 user, website) -> list[dict]:
    """Ask Claude for buyer-intent prompt questions grounded in the business.

    Returns register-ready dicts ({"text", "type"}), or [] on any failure so
    the caller can fall back to templates.
    """
    if not (description or business_name):
        return []
    provider = ClaudeUtility(model="claude-haiku-4-5", max_tokens=1200)
    if not provider.is_configured():
        return []

    bullets = ""
    if products:
        bullets = "\nProducts / offerings:\n- " + "\n- ".join(products[:6])

    prompt = (
        "You generate the exact questions real potential customers type into "
        "ChatGPT, Claude, or Perplexity when looking for a product or service "
        "like this business — so we can measure how often AI recommends it.\n\n"
        f"Business: {business_name}\n"
        f"Category: {industry or '(infer it from the description)'}\n"
        f"What it does: {description}{bullets}\n\n"
        f"Write exactly {count} questions that satisfy ALL of:\n"
        "1. Each is a natural question a human would actually type, ending "
        "with '?'. 6-20 words.\n"
        "2. Use the CORRECT real-world words for THIS business. If it deals "
        "with cars or car data, ask about cars / vehicles / car deals; a "
        "clinic asks about care / providers; a law firm about lawyers. Do "
        "NOT say 'software', 'SaaS', 'platform' or 'tool' unless the business "
        "genuinely is software. Match the noun to what it actually is.\n"
        "3. Do NOT name this business — we measure whether AI brings it up on "
        "its own.\n"
        "4. Cover a mix of intents: a direct recommendation, a comparison, "
        "alternatives to the market leader, a specific need or use-case, a "
        "beginner/overview question, and a buying-decision question.\n"
        "5. No year references and no superlatives like 'best ever'.\n\n"
        "Return ONLY a JSON array of question strings — no prose, no code fences."
    )

    result = provider.query(
        prompt, module="prompt_library", role="sample_generation",
        user=user, website=website,
    )
    if not result.succeeded:
        logger.debug("Sample-prompt LLM generation skipped: %s", result.error)
        return []

    match = re.search(r"\[.*\]", result.text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
    except Exception:
        return []
    if not isinstance(data, list):
        return []

    seen: set[str] = set()
    items: list[dict] = []
    for row in data:
        if isinstance(row, str):
            text = row
        elif isinstance(row, dict):
            text = row.get("text") or row.get("prompt") or ""
        else:
            continue
        text = (text or "").strip()
        key = text.lower()
        if len(text) < 8 or key in seen:
            continue
        seen.add(key)
        items.append({"text": text, "type": "custom"})
        if len(items) >= count:
            break
    return items


def build_sample_prompts(website, *, count: int, user) -> dict:
    """Read the site if needed, then generate business-grounded prompts.

    Returns {"items": [...], "industry": str, "source": "llm"|"template"|"none"}.
    ``source == "none"`` means we could not learn enough about the site to
    build anything relevant — the caller should ask the user for a
    description rather than emit a generic list.
    """
    industry, description, products = _scan_and_persist(website)

    items = _llm_prompts(
        business_name=website.name or "", industry=industry,
        description=description, products=products, count=count,
        user=user, website=website,
    )
    if items:
        return {"items": items, "industry": industry, "source": "llm"}

    # Deterministic fallback — but ONLY with a real industry. We never emit
    # the old generic "software" template set for a non-software site.
    if industry:
        from apps.llm_ranking.services.prompt_library import PromptLibrary
        base = PromptLibrary.generate(
            industry=industry, business_name=website.name or "", max_prompts=count,
        )
        items = [{"text": p["text"], "type": p.get("intent", "custom")} for p in base]
        return {"items": items, "industry": industry, "source": "template"}

    return {"items": [], "industry": "", "source": "none"}
