import json
import logging
import re

from django.conf import settings

from apps.competitors.models import Competitor

logger = logging.getLogger("apps")


_SUGGEST_MODEL = "claude-haiku-4-5"
_SUGGEST_PROMPT = """You are a competitive-analysis assistant. Suggest 5-7 real
competitor companies for the business below. Only include genuine competitors
that any informed buyer would compare with — no generic categories or made-up
names.

Business name: {name}
Industry: {industry}
Website: {url}
Description: {description}

Return strict JSON only, an array of objects with this shape:
[
  {{"name": "Acme Inc", "domain": "acme.com", "reason": "Direct competitor in core market"}}
]
No prose before or after the JSON."""


def _call_haiku_for_suggestions(prompt: str) -> str:
    """Single Haiku call. Raises on any failure so the caller can react."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=_SUGGEST_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    # Best-effort token usage tracking — never blocks the suggestion call.
    try:
        from core.ai_tracking import record_usage
        record_usage(
            module="competitor_discovery",
            model_name=_SUGGEST_MODEL,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
    except Exception:
        pass
    return resp.content[0].text.strip()


def _normalise_domain(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip().lower().replace("https://", "").replace("http://", "")
    s = s.replace("www.", "").split("/")[0]
    return s


class DiscoveryService:
    @staticmethod
    def auto_detect(*, website) -> list:
        """Auto-detect competitors for an existing website."""
        return DiscoveryService.suggest(
            name=getattr(website, "name", "") or "",
            industry=getattr(website, "industry", "") or "",
            url=getattr(website, "url", "") or "",
            description=getattr(website, "description", "") or "",
        )

    @staticmethod
    def suggest(
        *,
        name: str = "",
        industry: str = "",
        url: str = "",
        description: str = "",
    ) -> list[dict]:
        """
        Use Claude Haiku to suggest 5-7 likely competitor companies based on
        the business context. Returns an empty list when the model is not
        configured or the response can't be parsed — never raises so callers
        can render an empty state cleanly.
        """
        if not getattr(settings, "ANTHROPIC_API_KEY", ""):
            logger.info("Competitor suggestion skipped: ANTHROPIC_API_KEY missing")
            return []
        if not (name or industry or url):
            return []

        filled_prompt = _SUGGEST_PROMPT.format(
            name=name or "(unspecified)",
            industry=industry or "(unspecified)",
            url=url or "(none)",
            description=(description or "")[:1000] or "(none provided)",
        )

        try:
            raw = _call_haiku_for_suggestions(filled_prompt)
        except Exception as exc:
            logger.warning("Competitor suggestion call failed: %s", exc)
            return []

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            return []

        results: list[dict] = []
        seen: set = set()
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            entry_name = (entry.get("name") or "").strip()
            domain = _normalise_domain(entry.get("domain") or "")
            if not entry_name or not domain or domain in seen:
                continue
            seen.add(domain)
            results.append({
                "name": entry_name[:200],
                "domain": domain[:200],
                "reason": (entry.get("reason") or "").strip()[:300],
            })
            if len(results) >= 7:
                break
        return results

    @staticmethod
    def add_competitor(*, website, competitor_url: str, name: str = "") -> Competitor:
        """Manually add a competitor to track."""
        from core.exceptions import CompetitorLimitReached
        from core.permissions.feature_flags import get_competitor_limit

        limit = get_competitor_limit(website.user)
        current = Competitor.objects.filter(website=website).count()
        if current >= limit:
            raise CompetitorLimitReached()

        competitor, created = Competitor.objects.get_or_create(
            website=website,
            competitor_url=competitor_url,
            defaults={"name": name or competitor_url},
        )
        return competitor
