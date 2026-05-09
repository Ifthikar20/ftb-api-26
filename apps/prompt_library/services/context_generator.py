"""Generate a batch of templated prompts from a free-form user context.

Calls the synthesis provider (DeepSeek by default; Anthropic when DeepSeek
isn't configured) with a strict-JSON instruction asking for ``count`` diverse,
natural-feeling templated prompts in the style of questions a real person
might ask an AI assistant. Returns a list of envelopes the API layer can
serialise or persist.

The function is defensive: any error path (no provider configured, malformed
JSON, truncated response, network exception) returns a deterministic
single-prompt fallback so the UI never crashes.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from apps.prompt_library.services.template_parser import extract_variables

logger = logging.getLogger("apps")

ALLOWED_STYLES = {"story", "question", "comparison", "local", "how_to", "listicle"}
ALLOWED_BUCKETS = {"category", "comparison", "problem", "local"}

_SYSTEM = (
    "You are a senior researcher who writes natural-feeling questions people "
    "ask AI assistants like ChatGPT, Claude, Gemini, and Perplexity in real "
    "life. Your questions should sound like something a real person typed — "
    "first-person, conversational, sometimes meandering. They should NOT "
    "sound like SEO listicle prompts (no 'best X 2026', 'top 10 Y').\n\n"
    "You write each prompt as a TEMPLATE using `{{ variable }}` placeholders "
    "for the parts that vary across businesses (company name, location, "
    "product, etc). Variable names use snake_case.\n\n"
    "Reasonable variable names to reuse where applicable: company_name, "
    "brand, location, location_hint, location_information, core_idea, "
    "product_category, sales_item, audience, time_of_day, persona, "
    "source_medium."
)

_USER_TEMPLATE = (
    "Generate {count} DISTINCT prompts inspired by the following user context. "
    "Mix styles: 8 stories, 5 questions, 4 problems, 3 local-flavored. Vary "
    "length (short crisp questions to multi-sentence stories). Each prompt "
    "should feel NATURAL and HUMAN.\n\n"
    'CONTEXT: """{context_text}"""\n\n'
    "Output strict JSON: a list of {count} objects, each with these keys:\n"
    "  template_text  (string with {{{{ var }}}} slots)\n"
    "  style          (one of: story, question, comparison, local, how_to, listicle)\n"
    "  intent_bucket  (one of: category, comparison, problem, local)\n"
    "  preview_text   (the template filled with plausible values inferred from CONTEXT)\n\n"
    "Return ONLY the JSON array, no commentary."
)


def _strip_fences(text: str) -> str:
    """Drop ```json ... ``` markdown fences if the model added them."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _extract_json_array(text: str) -> list[Any]:
    """Pull the first JSON array out of text. Attempt a best-effort repair
    when the response is truncated mid-object."""
    if not text:
        return []
    text = _strip_fences(text)
    match = re.search(r"\[.*", text, re.DOTALL)
    if not match:
        return []
    candidate = match.group()
    # Direct parse first.
    try:
        data = json.loads(candidate)
        return data if isinstance(data, list) else []
    except Exception:
        pass
    # Repair attempt: trim to last complete object and close the array.
    last_brace = candidate.rfind("}")
    if last_brace == -1:
        return []
    repaired = candidate[: last_brace + 1] + "]"
    try:
        data = json.loads(repaired)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _fallback_single(context_text: str) -> list[dict]:
    """Deterministic safety net so the UI always has at least one card."""
    template = (
        "I keep hearing about {{ company_name }} in {{ location }}. "
        "Is it legit?"
    )
    return [
        {
            "template_text": template,
            "template_variables": extract_variables(template),
            "style": "question",
            "intent_bucket": "category",
            "preview_text": (context_text or "Tell me about this place.").strip()[:200],
        }
    ]


def _normalise_item(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    template_text = str(raw.get("template_text") or "").strip()
    if len(template_text) < 10:
        return None
    style = str(raw.get("style") or "question").strip().lower()
    if style not in ALLOWED_STYLES:
        style = "question"
    bucket = str(raw.get("intent_bucket") or "category").strip().lower()
    if bucket not in ALLOWED_BUCKETS:
        bucket = "category"
    preview_text = str(raw.get("preview_text") or "").strip()
    return {
        "template_text": template_text,
        "template_variables": extract_variables(template_text),
        "style": style,
        "intent_bucket": bucket,
        "preview_text": preview_text or template_text,
    }


def generate_from_context(
    context_text: str,
    *,
    count: int = 20,
    user=None,
) -> tuple[list[dict], str]:
    """Return (items, provider_name).

    ``provider_name`` is the synthesis provider that produced the items
    ("deepseek", "claude", ...) or "fallback" if no provider was usable.
    """
    context_text = (context_text or "").strip()
    if not context_text:
        return _fallback_single(""), "fallback"

    try:
        from apps.llm_ranking.providers import get_synthesis_provider
    except Exception as exc:  # pragma: no cover — import-time only
        logger.warning("context_generator: provider import failed: %s", exc)
        return _fallback_single(context_text), "fallback"

    provider = get_synthesis_provider()
    if provider is None:
        return _fallback_single(context_text), "fallback"

    user_prompt = _USER_TEMPLATE.format(count=count, context_text=context_text)
    try:
        result = provider.query(
            user_prompt,
            _SYSTEM,
            user=user,
            website=None,
            audit_id="prompt_library_context_generator",
            role="synthesis",
        )
    except Exception as exc:
        logger.warning("context_generator provider call failed: %s", exc)
        return _fallback_single(context_text), getattr(provider, "name", "fallback")

    if not getattr(result, "succeeded", False):
        return _fallback_single(context_text), getattr(provider, "name", "fallback")

    raw_items = _extract_json_array(getattr(result, "text", "") or "")
    items: list[dict] = []
    for raw in raw_items:
        norm = _normalise_item(raw)
        if norm is not None:
            items.append(norm)
        if len(items) >= count:
            break

    if not items:
        return _fallback_single(context_text), getattr(provider, "name", "fallback")

    return items, getattr(provider, "name", "deepseek")
