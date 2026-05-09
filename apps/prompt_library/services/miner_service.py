"""
Pluggable prompt miner.

Each miner implements :class:`BaseMiner` and is invoked by
:func:`mine_for_industry`. Miners gracefully no-op (with a logger
warning) when their credentials are missing, so the daily Celery
task can run on a half-configured environment without erroring.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings

from apps.prompt_library.models import IntentBucket, Prompt, PromptSource
from apps.prompt_library.services._hash import text_hash

logger = logging.getLogger("apps")


class BaseMiner:
    source: str = ""

    def fetch_questions(self, industry, limit: int) -> list[dict]:
        """Return a list of ``{text, source_url, intent_bucket}`` dicts.

        Subclasses must override. The miner is responsible for limiting
        the result count to ``limit`` and for picking an
        :class:`IntentBucket` value per row (default to ``CATEGORY``).
        """
        raise NotImplementedError


def _classify_intent(text: str) -> str:
    """Cheap rule-based intent bucketer. Good enough for the seed pass —
    the LLM-synth miner can override it explicitly."""
    t = (text or "").lower()
    if any(w in t for w in (" vs ", " versus ", "compare", "difference between", "alternative")):
        return IntentBucket.COMPARISON
    if any(w in t for w in ("near me", "in my area", "in ", "city", "local")):
        return IntentBucket.LOCAL
    if any(w in t for w in ("how do i", "how to", "fix", "problem", "error", "why does")):
        return IntentBucket.PROBLEM
    return IntentBucket.CATEGORY


class RedditMiner(BaseMiner):
    """Mines top questions from subreddits aligned to the industry slug.

    Uses praw if it is installed and ``REDDIT_CLIENT_ID`` /
    ``REDDIT_CLIENT_SECRET`` are configured. Otherwise falls back to
    Reddit's public ``.json`` endpoints via ``requests``.
    """

    source = PromptSource.REDDIT

    def fetch_questions(self, industry, limit: int) -> list[dict]:
        client_id = getattr(settings, "REDDIT_CLIENT_ID", "")
        client_secret = getattr(settings, "REDDIT_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            logger.warning("RedditMiner: credentials missing, no-op")
            return []
        try:
            import requests
        except ImportError:  # pragma: no cover
            logger.warning("RedditMiner: requests not available")
            return []
        # Use the public JSON endpoint — keeps the dependency surface
        # small and avoids carrying praw across deployments.
        results: list[dict] = []
        subreddit = industry.slug.replace("-", "")
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{subreddit}/top.json",
                params={"limit": min(limit, 100), "t": "month"},
                headers={"User-Agent": "growthpilot-prompt-miner/0.1"},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            for child in resp.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                title = (d.get("title") or "").strip()
                if not title or "?" not in title:
                    continue
                results.append({
                    "text": title,
                    "source_url": "https://www.reddit.com" + d.get("permalink", ""),
                    "intent_bucket": _classify_intent(title),
                })
                if len(results) >= limit:
                    break
        except Exception as exc:
            logger.warning("RedditMiner failed: %s", exc)
        return results


class SerpApiMiner(BaseMiner):
    """Pulls People-Also-Ask + related questions for a category query."""

    source = PromptSource.SERPAPI

    def fetch_questions(self, industry, limit: int) -> list[dict]:
        api_key = getattr(settings, "SERPAPI_KEY", "")
        if not api_key:
            logger.warning("SerpApiMiner: SERPAPI_KEY missing, no-op")
            return []
        try:
            import requests
        except ImportError:  # pragma: no cover
            return []
        results: list[dict] = []
        try:
            resp = requests.get(
                "https://serpapi.com/search.json",
                params={"q": industry.name, "engine": "google", "api_key": api_key},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            for paa in (data.get("related_questions") or []):
                q = (paa.get("question") or "").strip()
                if not q:
                    continue
                results.append({
                    "text": q,
                    "source_url": paa.get("link", "") or "",
                    "intent_bucket": _classify_intent(q),
                })
                if len(results) >= limit:
                    break
            for rs in (data.get("related_searches") or []):
                if len(results) >= limit:
                    break
                q = (rs.get("query") or "").strip()
                if q:
                    results.append({
                        "text": q,
                        "source_url": rs.get("link", "") or "",
                        "intent_bucket": _classify_intent(q),
                    })
        except Exception as exc:
            logger.warning("SerpApiMiner failed: %s", exc)
        return results


class LLMSynthMiner(BaseMiner):
    """Synthesises canonical prompts via the existing Anthropic provider.

    Lazy-imports the LLM ranking provider registry so a missing
    Anthropic key results in a graceful no-op.
    """

    source = PromptSource.LLM_SYNTH

    META_PROMPT = (
        "Generate {limit} short, natural-language questions a real person "
        "would ask an AI assistant when researching the {industry} category. "
        "Mix four intent buckets in roughly equal proportions: category, "
        "comparison, problem, local. Return strict JSON: a list of "
        '{{"text": str, "intent_bucket": "category|comparison|problem|local"}} objects.'
    )

    def fetch_questions(self, industry, limit: int) -> list[dict]:
        try:
            from apps.llm_ranking.providers import get_provider
        except Exception as exc:  # pragma: no cover
            logger.warning("LLMSynthMiner: provider registry unavailable: %s", exc)
            return []
        provider = None
        for name in ("claude", "gpt4"):
            try:
                provider = get_provider(name)
                if provider is not None:
                    break
            except Exception:
                continue
        if provider is None:
            logger.warning("LLMSynthMiner: no provider configured, no-op")
            return []
        prompt = self.META_PROMPT.format(limit=limit, industry=industry.name)
        try:
            result = provider.query(prompt, "", user=None, website=None, audit_id="prompt_library_synth")
            text = getattr(result, "text", "") or ""
        except Exception as exc:
            logger.warning("LLMSynthMiner provider call failed: %s", exc)
            return []
        return _parse_synth_json(text, limit)


def _parse_synth_json(text: str, limit: int) -> list[dict]:
    import json
    import re

    match = re.search(r"\[.*\]", text or "", re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group())
    except Exception:
        return []
    out: list[dict] = []
    valid = {b.value for b in IntentBucket}
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        t = (item.get("text") or "").strip()
        bucket = item.get("intent_bucket") or IntentBucket.CATEGORY
        if bucket not in valid:
            bucket = IntentBucket.CATEGORY
        if t:
            out.append({"text": t, "source_url": "", "intent_bucket": bucket})
    return out


_REGISTRY = {
    "reddit": RedditMiner,
    "serpapi": SerpApiMiner,
    "llm_synth": LLMSynthMiner,
}


def mine_for_industry(
    industry,
    sources: Iterable[str] = ("reddit", "serpapi", "llm_synth"),
    limit: int = 200,
) -> dict:
    """Run each requested miner and persist new prompts.

    Returns a summary ``{source: count}`` dict. Exact duplicates (by
    ``text_hash``) are skipped silently; near-duplicate detection lives
    in :mod:`dedup_service` and runs at paraphrase time.
    """
    summary: dict[str, int] = {}
    for source in sources:
        cls = _REGISTRY.get(source)
        if cls is None:
            continue
        miner = cls()
        try:
            rows = miner.fetch_questions(industry, limit=limit)
        except Exception as exc:
            logger.warning("Miner %s raised: %s", source, exc)
            continue
        created = 0
        for row in rows:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            obj, was_created = Prompt.objects.get_or_create(
                industry=industry,
                text_hash=text_hash(text),
                defaults={
                    "text": text,
                    "intent_bucket": row.get("intent_bucket") or IntentBucket.CATEGORY,
                    "source": miner.source,
                    "source_url": row.get("source_url", "") or "",
                },
            )
            if was_created:
                created += 1
        summary[source] = created
    return summary
