"""Register audit-generated prompts into the prompt library.

Audits generate their own prompt set from business context rather than
reading the user's saved prompts. Those generated strings previously
existed only as free text on ``LLMRankingResult.prompt``, which left them
unaddressable: no ``Prompt`` row meant no id, so nothing in the UI could
link to a per-prompt detail view, and the library never reflected what
was actually measured.

Registering them closes that gap. Each generated prompt becomes a
``Prompt`` row (source ``llm_synth``) plus a ``BrandPrompt`` linking it to
the website, so:

* ``resolve_source_prompt_id`` matches at result-creation time and
  populates ``LLMRankingResult.source_prompt``
* the Overview's Top Prompts rows can deep-link to the detail page
* the Prompt Library shows what the audit actually asked

Registration is best-effort and idempotent — deduped on ``text_hash``.
It must never break an audit, so every failure is swallowed and logged.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")

# Audit intent tags -> the library's coarser IntentBucket choices.
_INTENT_MAP = {
    "recommendation": "category",
    "category": "category",
    "comparison": "comparison",
    "alternatives": "comparison",
    "use_case": "problem",
    "persona": "problem",
    "review": "problem",
    "local": "local",
}


def _bucket_for(intent: str) -> str:
    return _INTENT_MAP.get((intent or "").strip().lower(), "category")


def _industry_for(website):
    """Resolve the website's industry to an Industry row, else any active one.

    Mirrors the slug-or-name lookup used by the suggested-prompts view so a
    registered prompt lands in the same bucket the library would suggest.
    """
    from apps.prompt_library.models import Industry

    raw = (getattr(website, "industry", "") or "").strip()
    if raw:
        match = (
            Industry.objects.filter(is_active=True, slug__iexact=raw).first()
            or Industry.objects.filter(is_active=True, name__iexact=raw).first()
        )
        if match is not None:
            return match
    return Industry.objects.filter(is_active=True).first()


def register_generated_prompts(items: list[dict], website) -> int:
    """Upsert ``items`` (dicts with ``text``/``type``) into the library.

    Returns the number of prompts newly created. Never raises.
    """
    if not website or not items:
        return 0
    try:
        from apps.prompt_library.models import BrandPrompt, Prompt
        from apps.prompt_library.services._hash import text_hash

        industry = _industry_for(website)
        if industry is None:
            logger.debug("register_generated_prompts: no Industry rows available")
            return 0

        created = 0
        for item in items:
            text = (item.get("text") or "").strip() if isinstance(item, dict) else str(item).strip()
            if not text:
                continue
            digest = text_hash(text)
            prompt = Prompt.objects.filter(text_hash=digest).first()
            if prompt is None:
                prompt = Prompt.objects.create(
                    industry=industry,
                    text=text,
                    intent_bucket=_bucket_for(item.get("type") if isinstance(item, dict) else ""),
                    source="llm_synth",
                    excerpt=(item.get("rationale") or "")[:500] if isinstance(item, dict) else "",
                    text_hash=digest,
                    is_active=True,
                )
                created += 1
            # Link to the website so it shows in the library and the audit's
            # prompts are visible alongside anything the user curated.
            BrandPrompt.objects.get_or_create(website=website, prompt=prompt)
        return created
    except Exception as exc:  # pragma: no cover — registration is best-effort
        logger.warning("register_generated_prompts failed: %s", exc)
        return 0
