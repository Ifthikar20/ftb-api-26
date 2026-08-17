"""Convert raw user-typed prompt text into a templated prompt.

Calls the configured synthesis provider (DeepSeek by default when
configured, otherwise Anthropic) with a strict JSON schema. On any
error — provider unavailable, malformed JSON, etc — falls back to a
no-op result that wraps the raw text without templating.
"""
from __future__ import annotations

import json
import logging
import re

from apps.prompt_library.services.template_parser import extract_variables

logger = logging.getLogger("apps")

ALLOWED_STYLES = {"question", "story", "comparison", "local", "how_to", "listicle"}

_PROMPT = """You convert raw user-typed prompts into reusable templates with
{{ variable }} slots. Replace concrete brand names, locations, products,
and other tenant-specific nouns with snake_case placeholders. Keep the
sentence flow natural so the filled version reads exactly like the
original.

Return strict JSON ONLY (no prose, no markdown fences) with this shape:
{
  "template_text": "string with {{ variable }} placeholders",
  "template_variables": ["var_one", "var_two"],
  "style": "question | story | comparison | local | how_to | listicle"
}

Rules:
- Use snake_case for variable names.
- The "template_variables" list MUST exactly match the placeholders that
  appear in template_text.
- Pick the closest style. If unsure, use "question".
- Do NOT add any new variables that don't have a clear analogue in the
  source text — accuracy beats coverage.

Source text:
{raw}
""".strip()


def _extract_json(text: str) -> dict | None:
    """Pull the first balanced JSON object out of ``text``."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except Exception:
        return None


def _fallback(raw_text: str) -> dict:
    return {
        "template_text": raw_text or "",
        "template_variables": [],
        "style": "question",
    }


def auto_template(raw_text: str, *, user, website=None) -> dict:
    """Turn raw text into a template envelope. Always returns a dict.

    ``user`` is a required keyword so every call site attributes the LLM
    spend to a real account. Passing ``user=None`` disables the provider
    spend cap (core.ai_tracking) and is reserved for genuine system/test
    contexts — never for authenticated request handling.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return _fallback("")

    try:
        from apps.llm_ranking.providers import get_synthesis_provider
    except Exception as exc:  # pragma: no cover — import-time only
        logger.warning("auto_template: provider import failed: %s", exc)
        return _fallback(raw_text)

    provider = get_synthesis_provider()
    if provider is None:
        return _fallback(raw_text)

    try:
        # NB: use .replace, not .format — the prompt embeds a literal JSON
        # example with single { } braces that str.format would try to parse
        # as fields (and raise KeyError, silently no-op'ing this feature).
        result = provider.query(
            _PROMPT.replace("{raw}", raw_text),
            "You are a careful template extractor. Return JSON only.",
            user=user,
            website=website,
            audit_id="prompt_library_auto_template",
            role="synthesis",
        )
    except Exception as exc:
        logger.warning("auto_template provider call failed: %s", exc)
        return _fallback(raw_text)

    if not getattr(result, "succeeded", False):
        return _fallback(raw_text)

    payload = _extract_json(getattr(result, "text", "") or "")
    if not isinstance(payload, dict):
        return _fallback(raw_text)

    template_text = str(payload.get("template_text") or "").strip()
    if not template_text:
        return _fallback(raw_text)

    declared = payload.get("template_variables") or []
    if not isinstance(declared, list):
        declared = []
    # Trust the actual placeholders in the template text over whatever the
    # model declared in the side-list — declared list is informational.
    actual = extract_variables(template_text)
    style = str(payload.get("style") or "question").strip().lower()
    if style not in ALLOWED_STYLES:
        style = "question"
    return {
        "template_text": template_text,
        "template_variables": actual or [str(v) for v in declared if isinstance(v, str)],
        "style": style,
    }
