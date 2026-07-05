"""
Brand mention and sentiment extraction for Source Intelligence scans.

Given the text behind one search result (a Reddit thread with upvote
scores, or a page's visible text), a cheap Anthropic model extracts
which brands are discussed and how the content feels about each,
weighting community signals (upvotes) where present.

Follows the HaikuExtractionService conventions: strict-JSON prompt,
versioned template, central cost recording, graceful empty result when
the API key is absent or the call fails.
"""

from __future__ import annotations

import json
import logging
import time

from django.conf import settings

from core.ai_tracking import record_usage

logger = logging.getLogger("apps")

PROMPT_VERSION = "v2"
DEFAULT_MODEL = "claude-haiku-4-5"
MAX_CONTENT_CHARS = 16000

EXTRACTION_TEMPLATE = """You analyze web content for brand intelligence.

The user searched for: "{query}"
The brand we represent is: "{target_brand}"

Below is the content of one search result. If it is a Reddit thread,
comment upvote scores appear as [+N] and indicate community agreement:
weight higher-scored opinions more heavily.

Extract every brand, business, or product that the content expresses an
opinion about or recommends. Respond with ONLY valid JSON, no prose:

{{
  "brands": [
    {{
      "name": "<brand name, canonical capitalization>",
      "mentions": <int, how many distinct mentions>,
      "sentiment": <float -1.0 (hated) to 1.0 (loved), 0 = neutral/mixed>,
      "weight": <float 0-1, prominence in this content, upvote-adjusted>,
      "quotes": ["<up to 2 short verbatim quotes that best capture the opinion>"],
      "issues": ["<up to 3 short paraphrased problems or complaints people raise about this brand, empty if none>"]
    }}
  ],
  "target_brand_present": <true|false, is "{target_brand}" mentioned at all>,
  "relevant_to_query": <true|false, is this content actually about the topic of the search query>,
  "summary": "<one sentence: what this source says about the space>"
}}

Rules:
- Only include brands the content actually discusses; never invent.
- Max 10 brands, ordered by weight descending.
- Quotes must be verbatim substrings of the content.
- Set relevant_to_query to false when the content is about a different
  topic that merely shares words with the query (for example designer
  handbags when the query is about bagels).

CONTENT:
{content}
"""

RELEVANCE_TEMPLATE = """You filter web search results for topical relevance.

The user searched for: "{query}"

Below is the ranked result list (rank, title, url). Some results are
off-topic noise that merely shares words with the query (for example
designer handbag stores matching a "bagel" query). Judge each result
by its title and URL only.

Respond with ONLY valid JSON, no prose:

{{
  "results": [
    {{"rank": <int>, "relevant": <true|false>, "reason": "<short reason, only when false>"}}
  ]
}}

Include every rank exactly once. When unsure, lean relevant.

RESULTS:
{items}
"""


def _model_name() -> str:
    return (
        getattr(settings, "LLM_EXTRACTION_MODEL", "") or DEFAULT_MODEL
    )


def analyze_content(
    text: str,
    *,
    query: str,
    target_brand: str,
    website=None,
    user=None,
) -> dict:
    """Extract brand sentiment from one result's content.

    Returns {"brands": [...], "target_brand_present": bool, "summary": str}
    or {"brands": [], "error": "..."} when unavailable/failed.
    """
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key:
        return {"brands": [], "error": "no_api_key"}
    if not (text or "").strip():
        return {"brands": [], "error": "empty_content"}

    try:
        import anthropic
    except ImportError:
        return {"brands": [], "error": "anthropic_not_installed"}

    prompt = EXTRACTION_TEMPLATE.format(
        query=query,
        target_brand=target_brand or "unknown",
        content=text[:MAX_CONTENT_CHARS],
    )

    started = time.monotonic()
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=_model_name(),
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.warning("Source sentiment extraction failed: %s", exc)
        return {"brands": [], "error": str(exc)[:200]}

    duration_ms = int((time.monotonic() - started) * 1000)
    usage = getattr(resp, "usage", None)
    record_usage(
        module="source_sentiment",
        model_name=_model_name(),
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        user=user,
        website=website,
        duration_ms=duration_ms,
        metadata={"prompt_version": PROMPT_VERSION},
    )

    raw = "".join(
        getattr(block, "text", "") or "" for block in (getattr(resp, "content", None) or [])
    ).strip()
    # Tolerate accidental code fences around the JSON.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        data = json.loads(raw)
    except ValueError:
        logger.warning("Source sentiment returned non-JSON (first 200): %r", raw[:200])
        return {"brands": [], "error": "non_json_response"}

    brands = []
    for item in (data.get("brands") or [])[:10]:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        brands.append({
            "name": name,
            "mentions": max(0, int(item.get("mentions") or 0)),
            "sentiment": max(-1.0, min(1.0, float(item.get("sentiment") or 0.0))),
            "weight": max(0.0, min(1.0, float(item.get("weight") or 0.0))),
            "quotes": [str(q)[:300] for q in (item.get("quotes") or [])[:2]],
            "issues": [str(i)[:200] for i in (item.get("issues") or [])[:3]],
        })
    return {
        "brands": brands,
        "target_brand_present": bool(data.get("target_brand_present")),
        # Default True: older prompt versions and partial responses must
        # not cause content to be discarded.
        "relevant_to_query": bool(data.get("relevant_to_query", True)),
        "summary": str(data.get("summary") or "")[:500],
    }


def assess_serp_relevance(
    query: str,
    items: list[dict],
    *,
    website=None,
    user=None,
) -> dict[int, dict]:
    """Judge SERP items against the query in ONE cheap model call.

    Runs before any content fetch so off-topic results cost nothing
    downstream. Returns {rank: {"relevant": bool, "reason": str}}.
    Fails open: on missing key, API error, or malformed output every
    rank is reported relevant so a scan never dies on the gate.
    """
    all_relevant = {
        int(item["rank"]): {"relevant": True, "reason": ""} for item in items
    }
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if not api_key or not items:
        return all_relevant

    try:
        import anthropic
    except ImportError:
        return all_relevant

    listing = "\n".join(
        f'{item["rank"]}. "{(item.get("title") or "")[:200]}" — {item.get("url", "")[:300]}'
        for item in items
    )
    prompt = RELEVANCE_TEMPLATE.format(query=query, items=listing)

    started = time.monotonic()
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=_model_name(),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.warning("SERP relevance gate failed (fail-open): %s", exc)
        return all_relevant

    duration_ms = int((time.monotonic() - started) * 1000)
    usage = getattr(resp, "usage", None)
    record_usage(
        module="source_relevance",
        model_name=_model_name(),
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        user=user,
        website=website,
        duration_ms=duration_ms,
        metadata={"prompt_version": PROMPT_VERSION},
    )

    raw = "".join(
        getattr(block, "text", "") or "" for block in (getattr(resp, "content", None) or [])
    ).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        data = json.loads(raw)
    except ValueError:
        logger.warning("SERP relevance gate returned non-JSON (fail-open)")
        return all_relevant

    verdicts = dict(all_relevant)
    for entry in data.get("results") or []:
        try:
            rank = int(entry.get("rank"))
        except (TypeError, ValueError):
            continue
        if rank in verdicts:
            verdicts[rank] = {
                "relevant": bool(entry.get("relevant", True)),
                "reason": str(entry.get("reason") or "")[:200],
            }
    return verdicts
