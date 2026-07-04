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

ALLOWED_STYLES = {
    "story",          # multi-sentence anecdote
    "question",       # direct, single-sentence
    "comparison",     # X vs Y
    "local",          # mentions place / route / time
    "how_to",         # instructional
    "listicle",       # ranking-style
    "recommendation", # asking for picks
    "skeptical",      # doubting a claim
    "discovery",      # 'I just heard / saw...'
    "problem",        # frustrated user trying to fix something
    "verification",   # 'is X legit?'
    "experience",     # first-person 'I tried X'
}
ALLOWED_BUCKETS = {"category", "comparison", "problem", "local"}

_SYSTEM = (
    "You are a senior researcher who writes natural-feeling questions people "
    "ask AI assistants like ChatGPT, Claude, Gemini, and Perplexity in real "
    "life. Your prompts should sound like something a real person typed — "
    "first-person, conversational, sometimes meandering, sometimes terse. "
    "They should NOT sound like SEO listicle headlines (no 'best X 2026', "
    "'top 10 Y'). They should feel like overheard chatter, group-chat asks, "
    "Reddit posts, or driving-around questions.\n\n"
    "Each prompt MUST be CONCRETE. Invent or recall plausible business names, "
    "real-sounding locations, persona details, and specific contexts based on "
    "the user's input. Do NOT use placeholder syntax like '{{ company_name }}' "
    "or 'Brand X'. Use specific (invented if needed) names like 'Dave's Bagels' "
    "or 'Morningside Bakery'.\n\n"
    "Mix tones: skeptical, curious, frustrated, excited, gossipy, lazy."
)

_USER_TEMPLATE = (
    "Generate {count} DISTINCT, fully-concrete prompts inspired by the user "
    "context below. Each prompt should reference plausible specific names, "
    "places, or persona details — invent them if needed (5-10 different "
    "made-up business names is fine; reuse them across prompts to feel like "
    "the same neighbourhood).\n\n"
    "MIX LENGTHS DELIBERATELY:\n"
    "- 4 short prompts (one sentence, ≤ 15 words, terse)\n"
    "- 8 medium prompts (2 sentences, 15-30 words)\n"
    "- 8 long prompts (3-4 sentences, 30-60 words, anecdotal, conversational, "
    "with side comments and personal context)\n\n"
    "MIX STYLES across the {count} items. Use as many of these styles as "
    "possible: story, question, comparison, local, how_to, recommendation, "
    "skeptical, discovery, problem, verification, experience. Aim for at "
    "least 7 different style values.\n\n"
    'CONTEXT: """{context_text}"""\n\n'
    "Output strict JSON: a list of {count} objects, each with these keys:\n"
    "  prompt_text    (string — the full, concrete prompt text. No placeholders.)\n"
    "  style          (one of: story, question, comparison, local, how_to, "
    "listicle, recommendation, skeptical, discovery, problem, verification, "
    "experience)\n"
    "  intent_bucket  (one of: category, comparison, problem, local)\n"
    "  trend_score    (integer 0-100; your best estimate of how popular / "
    "trending this question is on Google right now, where 100 = extremely "
    "common search intent and 0 = obscure niche)\n"
    "  keywords       (array of 3-6 short EXACT substrings from prompt_text "
    "that are the MOST demand-driving phrases — neighbourhood, brand, "
    "category-specific terminology, distinctive adjectives in quotes. "
    "Each substring MUST appear verbatim in prompt_text.)\n"
    "  seen_in        (one of: reddit, quora, google_search, hacker_news, "
    "yelp, tiktok, youtube_comments, twitter, forum, news_comments, "
    "ai_chat — the SINGLE most-likely real-world surface where a person "
    "would actually post or type this exact question)\n"
    "  community      (optional short string — when seen_in is reddit, the "
    "subreddit name like 'r/saas'; when quora a topic; when youtube a "
    "channel handle. Empty string if no obvious match.)\n\n"
    "Vary seen_in deliberately across the batch — some prompts are Reddit-"
    "shaped, others Quora, others typed straight into ChatGPT. Don't put "
    "everything in one bucket.\n\n"
    "Return ONLY the JSON array, no commentary."
)


# Compact instruction for the related-prompt recommender. Kept intentionally
# small (this is a secondary feature) to minimise DeepSeek token spend.
_RELATED_SYSTEM = (
    "You write short, natural questions a real person would ask an AI "
    "assistant. Reply with JSON only."
)

_RELATED_USER_TEMPLATE = (
    'Existing prompt: "{seed}"\n'
    "Write {count} short related questions on the same topic and audience, "
    "each from a different angle. Be concrete; no placeholders.\n"
    'Return only a JSON array of objects with keys: "prompt_text" (string), '
    '"style" (one of question, comparison, how_to, local, problem), '
    '"intent_bucket" (one of category, comparison, problem, local).'
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
    """Deterministic safety net so the UI always has at least one row.

    Uses the user's context verbatim (truncated) so the result is at least
    contextually relevant when the synthesis provider is unavailable.
    """
    ctx = (context_text or "").strip() or "this scenario"
    prompt_text = (
        f"Has anyone here actually checked out the spots involved in: "
        f"{ctx[:240]}? Looking for honest takes."
    )
    word_count = len([w for w in prompt_text.split() if w])
    if word_count <= 14:
        length_band = "short"
    elif word_count <= 30:
        length_band = "medium"
    else:
        length_band = "long"
    return [
        {
            "template_text": prompt_text,
            "template_variables": [],
            "prompt_text": prompt_text,
            "preview_text": prompt_text,
            "style": "question",
            "intent_bucket": "category",
            "trend_score": 50,
            "keywords": [],
            "word_count": word_count,
            "length_band": length_band,
            "seen_in": "ai_chat",
            "community": "",
        }
    ]


def _normalise_item(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    # Accept either the new concrete-prompt schema (prompt_text) or the older
    # template-with-placeholders schema (template_text) so older callers and
    # offline fixtures keep working.
    prompt_text = str(raw.get("prompt_text") or raw.get("template_text") or "").strip()
    if len(prompt_text) < 10:
        return None
    style = str(raw.get("style") or "question").strip().lower()
    if style not in ALLOWED_STYLES:
        style = "question"
    bucket = str(raw.get("intent_bucket") or "category").strip().lower()
    if bucket not in ALLOWED_BUCKETS:
        bucket = "category"
    try:
        trend_score = int(raw.get("trend_score", 50))
    except (TypeError, ValueError):
        trend_score = 50
    trend_score = max(0, min(100, trend_score))
    # Variables are extracted defensively — concrete prompts won't have any,
    # but if the model slips in a {{ slot }} we still capture it for storage.
    template_variables = extract_variables(prompt_text)
    # Keywords: keep only those that actually appear in the prompt text. The
    # frontend highlights them; nothing else, so verbatim match is the safest
    # contract.
    raw_keywords = raw.get("keywords") or []
    if isinstance(raw_keywords, str):
        raw_keywords = [raw_keywords]
    keywords: list[str] = []
    seen: set[str] = set()
    lower_prompt = prompt_text.lower()
    for kw in raw_keywords:
        if not isinstance(kw, str):
            continue
        kw = kw.strip().strip("\"'")
        if len(kw) < 2 or kw.lower() not in lower_prompt:
            continue
        key = kw.lower()
        if key in seen:
            continue
        seen.add(key)
        keywords.append(kw)
        if len(keywords) >= 8:
            break
    # Word + length band — server-side so the frontend filter is just a
    # simple equality check.
    word_count = len([w for w in prompt_text.split() if w])
    if word_count <= 14:
        length_band = "short"
    elif word_count <= 30:
        length_band = "medium"
    else:
        length_band = "long"
    # 'seen_in' — the real-world surface where this prompt is most likely
    # to be asked. Validated against an allow-list; fall back to 'ai_chat'
    # which is the safest assumption ("typed into ChatGPT directly").
    ALLOWED_SEEN_IN = {
        "reddit", "quora", "google_search", "hacker_news", "yelp",
        "tiktok", "youtube_comments", "twitter", "forum",
        "news_comments", "ai_chat",
    }
    seen_in = str(raw.get("seen_in") or "ai_chat").strip().lower().replace("-", "_").replace(" ", "_")
    if seen_in not in ALLOWED_SEEN_IN:
        seen_in = "ai_chat"
    community = str(raw.get("community") or "").strip()
    if len(community) > 80:
        community = community[:80]
    return {
        # Legacy fields kept for storage/compat with the existing Prompt model.
        "template_text": prompt_text,
        "template_variables": template_variables,
        "preview_text": prompt_text,
        # Primary field the new UI surfaces.
        "prompt_text": prompt_text,
        "style": style,
        "intent_bucket": bucket,
        "trend_score": trend_score,
        "keywords": keywords,
        "word_count": word_count,
        "length_band": length_band,
        "seen_in": seen_in,
        "community": community,
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


def generate_related_prompts(
    seed_prompt: str,
    *,
    count: int = 5,
    user=None,
) -> tuple[list[dict], str]:
    """Return (items, provider_name) of prompts related to ``seed_prompt``.

    Best-effort recommender used by the create-prompt flow to suggest
    follow-on prompts. Because this is a secondary operation (not a core
    audit) it is kept deliberately cheap:

    * Pins DeepSeek (the cheapest tooling provider) rather than the default
      synthesis chain. A safety fallback to Claude/GPT only kicks in when
      DeepSeek has no key configured.
    * Uses a small system + user instruction and a low ``count`` to minimise
      token spend.

    Token usage is still metered per-user: passing ``user`` to
    ``provider.query`` records an ``AITokenUsage`` row (tagged role
    "recommendation") that counts toward the user's usage and monthly cost
    cap. Returns an empty list on any failure so the UI just shows nothing.
    """
    seed = (seed_prompt or "").strip()
    if not seed:
        return [], "fallback"
    count = max(1, min(int(count or 5), 10))

    try:
        from apps.llm_ranking.providers import get_synthesis_provider
    except Exception as exc:  # pragma: no cover — import-time only
        logger.warning("generate_related_prompts: provider import failed: %s", exc)
        return [], "fallback"

    provider = get_synthesis_provider("deepseek")
    if provider is None:
        return [], "fallback"

    user_prompt = _RELATED_USER_TEMPLATE.format(seed=seed[:300], count=count)
    try:
        result = provider.query(
            user_prompt,
            _RELATED_SYSTEM,
            user=user,
            website=None,
            audit_id="prompt_library_related",
            role="recommendation",
        )
    except Exception as exc:
        logger.warning("generate_related_prompts provider call failed: %s", exc)
        return [], getattr(provider, "name", "fallback")

    if not getattr(result, "succeeded", False):
        return [], getattr(provider, "name", "fallback")

    items: list[dict] = []
    for raw in _extract_json_array(getattr(result, "text", "") or ""):
        norm = _normalise_item(raw)
        if norm is not None:
            items.append(norm)
        if len(items) >= count:
            break
    return items, getattr(provider, "name", "deepseek")
