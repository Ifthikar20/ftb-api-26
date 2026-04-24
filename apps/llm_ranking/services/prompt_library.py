"""
Prompt library for LLM Ranking audits.

The catalogue lives in JSON files under `apps/llm_ranking/prompt_packs/`:

  default.json        — industry-agnostic base set (always loaded)
  saas.json           — B2B SaaS
  ecommerce.json      — e-commerce / DTC
  legal.json          — law firms and legal services
  agency.json         — marketing / creative agencies
  healthcare.json     — clinics and telehealth

Each pack ships with a `industry_keys` list; when an audit's industry string
matches any of those keys (case-insensitive substring match), the pack is
layered over the default set. The final mix is intent-balanced so no single
query shape dominates the benchmark.

Why JSON instead of Python:
- Non-engineers can edit prompts without a deploy (PR on a json file).
- Industry packs are self-contained and trivial to add (drop a new file).
- Future `PromptPack` Django model can persist overrides above these defaults
  without redesigning the schema.

Each JSON pack matches this shape:

  {
    "schema": "prompt-pack/v1",
    "name": "...",
    "description": "...",
    "industry_keys": ["..."],
    "prompts": [
      {"text": "...", "intent": "recommendation", "placeholders": ["industry"]}
    ]
  }
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("apps")

PACK_DIR = Path(__file__).resolve().parent.parent / "prompt_packs"
DEFAULT_PACK = "default"

# Intent weighting. Controls how many prompts from each intent bucket the
# sampler tries to take. Tunable here (not in JSON) because it's about
# sampling strategy, not prompt content.
INTENT_PRIORITY: tuple[tuple[str, int], ...] = (
    ("recommendation", 2),
    ("comparison",     2),
    ("use_case",       2),
    ("alternatives",   1),
    ("category",       1),
    ("persona",        1),
    ("review",         1),
    ("local",          1),
)

VALID_INTENTS: frozenset = frozenset(i for i, _ in INTENT_PRIORITY)


@dataclass(frozen=True)
class PromptTemplate:
    text: str
    intent: str
    placeholders: frozenset = field(default_factory=frozenset)

    def fill(self, **kwargs) -> str:
        safe = {k: v for k, v in kwargs.items() if k in self.placeholders}
        return self.text.format(**safe) if self.placeholders else self.text


@dataclass(frozen=True)
class PromptPack:
    name: str
    description: str
    industry_keys: tuple[str, ...]
    templates: tuple[PromptTemplate, ...]


# ── Pack loading ──────────────────────────────────────────────────────────────

def _parse_pack(data: dict) -> PromptPack:
    """Convert a raw JSON dict into a PromptPack. Drops malformed entries."""
    templates: list[PromptTemplate] = []
    for raw in data.get("prompts", []) or []:
        if not isinstance(raw, dict):
            continue
        text = (raw.get("text") or "").strip()
        intent = (raw.get("intent") or "").strip()
        if not text or intent not in VALID_INTENTS:
            continue
        placeholders = frozenset(raw.get("placeholders") or [])
        templates.append(PromptTemplate(text=text, intent=intent, placeholders=placeholders))
    return PromptPack(
        name=str(data.get("name") or "Unnamed"),
        description=str(data.get("description") or ""),
        industry_keys=tuple(str(k).lower() for k in (data.get("industry_keys") or [])),
        templates=tuple(templates),
    )


@lru_cache(maxsize=32)
def load_pack(name: str) -> PromptPack | None:
    """Load a single pack by filename stem. Returns None if the file is missing."""
    path = PACK_DIR / f"{name}.json"
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.warning("Failed to load prompt pack %s: %s", name, exc)
        return None
    return _parse_pack(data)


def list_available_packs() -> list[str]:
    """Names of all JSON files in the pack directory (without extension)."""
    if not PACK_DIR.is_dir():
        return []
    return sorted(p.stem for p in PACK_DIR.glob("*.json"))


def _industry_packs() -> list[PromptPack]:
    """Every pack except the default, loaded and cached."""
    packs: list[PromptPack] = []
    for name in list_available_packs():
        if name == DEFAULT_PACK:
            continue
        pack = load_pack(name)
        if pack is not None:
            packs.append(pack)
    return packs


def match_industry_pack(industry: str) -> PromptPack | None:
    """Return the first industry pack whose keys match the given industry string.

    Matching is case-insensitive substring: pack key "saas" matches
    "SaaS analytics" or "B2B SaaS". First match wins (packs are scanned in
    alphabetical order).
    """
    if not industry:
        return None
    haystack = industry.lower()
    for pack in _industry_packs():
        for key in pack.industry_keys:
            if key and key in haystack:
                return pack
    return None


# ── Sampling ─────────────────────────────────────────────────────────────────

def _dedupe_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _bucket_by_intent(templates: Iterable[PromptTemplate]) -> dict[str, list[PromptTemplate]]:
    buckets: dict[str, list[PromptTemplate]] = {intent: [] for intent in VALID_INTENTS}
    for t in templates:
        buckets.setdefault(t.intent, []).append(t)
    return buckets


class PromptLibrary:
    """
    Generates an intent-balanced prompt set for an audit.

    The default pack is always loaded. If `industry` matches one of the
    industry packs, its templates are layered in FIRST within each intent
    bucket so the industry-specific phrasings take priority over the
    generic defaults.
    """

    DEFAULT_MAX = 10

    # ── Public API ────────────────────────────────────────────────────────

    @classmethod
    def generate(
        cls,
        *,
        industry: str,
        use_case: str = "",
        location: str = "",
        max_prompts: int = DEFAULT_MAX,
        themes: list | None = None,
    ) -> list[dict]:
        """Return a list of {"text": str, "intent": str} dicts.

        `themes` (optional) restricts sampling to a subset of intents.
        Empty / None means use the default INTENT_PRIORITY mix.
        """
        industry_norm = (industry or "software").strip()
        use_case_norm = (use_case or industry_norm).strip()
        location_norm = (location or "").strip()
        allowed = {t for t in (themes or []) if t in VALID_INTENTS} or None

        templates = cls._resolved_templates(industry_norm)
        buckets = _bucket_by_intent(templates)

        picked: list[dict] = []
        seen_texts: set = set()

        for intent, take_n in INTENT_PRIORITY:
            if allowed is not None and intent not in allowed:
                continue
            # Skip `local` unless a location is provided — filling without
            # location yields broken prompts.
            if intent == "local" and not location_norm:
                continue
            bucket = buckets.get(intent, [])
            taken = 0
            for template in bucket:
                if taken >= take_n:
                    break
                try:
                    text = template.fill(
                        industry=industry_norm,
                        use_case=use_case_norm,
                        location=location_norm,
                    )
                except KeyError:
                    continue
                key = text.strip().lower()
                if not text or key in seen_texts:
                    continue
                seen_texts.add(key)
                picked.append({"text": text, "intent": intent})
                taken += 1
                if len(picked) >= max_prompts:
                    return picked

        return picked

    @classmethod
    def generate_texts(
        cls,
        *,
        industry: str,
        use_case: str = "",
        location: str = "",
        max_prompts: int = DEFAULT_MAX,
        themes: list | None = None,
    ) -> list[str]:
        return [
            p["text"] for p in cls.generate(
                industry=industry,
                use_case=use_case,
                location=location,
                max_prompts=max_prompts,
                themes=themes,
            )
        ]

    @classmethod
    def intents_for(cls, prompt_texts: Iterable[str]) -> list[str]:
        """Best-effort intent tag for arbitrary prompt text.

        Uses substring matching against every known template (with
        placeholders stripped) so a generated-and-filled prompt still maps
        back to its source intent.
        """
        index: dict[str, str] = {}
        for t in cls._resolved_templates(industry=""):
            normalised = t.text.lower()
            for ph in t.placeholders:
                normalised = normalised.replace("{" + ph + "}", "")
            key = " ".join(normalised.split())
            if key:
                index[key] = t.intent

        out: list[str] = []
        for text in prompt_texts:
            lower = " ".join(text.lower().split())
            matched = "custom"
            for key, intent in index.items():
                if key and key in lower:
                    matched = intent
                    break
            out.append(matched)
        return out

    @classmethod
    def resolved_pack_names(cls, industry: str) -> list[str]:
        """Debug / UI helper: which packs are active for this industry?"""
        used = [DEFAULT_PACK]
        pack = match_industry_pack(industry)
        if pack is not None:
            # Find the filename for this pack so callers can show "saas"
            for name in list_available_packs():
                if name == DEFAULT_PACK:
                    continue
                loaded = load_pack(name)
                if loaded is not None and loaded.name == pack.name:
                    used.append(name)
                    break
        return used

    # ── Internals ─────────────────────────────────────────────────────────

    @classmethod
    def _resolved_templates(cls, industry: str) -> tuple[PromptTemplate, ...]:
        """Combine the default pack with the matching industry pack (if any).

        Industry templates come first so the sampler prefers them when
        filling each intent bucket, before falling back to default phrasings.
        """
        default = load_pack(DEFAULT_PACK)
        default_templates = default.templates if default else ()
        industry_pack = match_industry_pack(industry) if industry else None
        industry_templates = industry_pack.templates if industry_pack else ()
        # Dedupe by exact (intent, text) pair to avoid duplicates when an
        # industry pack reuses a default-style phrasing.
        seen: set = set()
        merged: list[PromptTemplate] = []
        for t in (*industry_templates, *default_templates):
            sig = (t.intent, t.text.strip().lower())
            if sig in seen:
                continue
            seen.add(sig)
            merged.append(t)
        return tuple(merged)
