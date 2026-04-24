"""
Prompt library for LLM Ranking audits.

Each prompt simulates a realistic buyer query a user would type into an
AI assistant. Templates are organised by *intent* (recommendation, comparison,
alternatives, use-case, category, local, persona, review) because different
intents surface different sets of results from the same LLM.

Why intents matter for benchmarking:
- A "recommendation" query often returns a single top pick.
- A "comparison" query typically returns a ranked list of 3-10.
- An "alternatives" query surfaces a competitor set.
- A "persona" query ("for a 5-person startup") returns fit-for-segment answers.
Mixing them gives a more honest picture of how a brand performs across the
purchase funnel, instead of over-fitting to one question shape.
"""
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PromptTemplate:
    text: str
    intent: str
    # Placeholders present in the text; used for strict templating.
    placeholders: frozenset = field(default_factory=frozenset)

    def fill(self, **kwargs) -> str:
        # Only substitute placeholders this template actually declared —
        # avoids KeyError on templates that don't use every variable.
        safe = {k: v for k, v in kwargs.items() if k in self.placeholders}
        return self.text.format(**safe) if self.placeholders else self.text


# ── Template sets by intent ──────────────────────────────────────────────────

# Recommendation — "what should I use"
RECOMMENDATION = [
    PromptTemplate(
        "What are the best {industry} tools available right now?",
        "recommendation", frozenset({"industry"})),
    PromptTemplate(
        "Which {industry} solutions do most companies use?",
        "recommendation", frozenset({"industry"})),
    PromptTemplate(
        "What are the leading {industry} products recommended by experts?",
        "recommendation", frozenset({"industry"})),
    PromptTemplate(
        "If you had to recommend one {industry} platform today, which would it be and why?",
        "recommendation", frozenset({"industry"})),
]

# Comparison — explicit "X vs Y" shape
COMPARISON = [
    PromptTemplate(
        "Compare the top 5 {industry} platforms and explain their strengths.",
        "comparison", frozenset({"industry"})),
    PromptTemplate(
        "Give me a side-by-side comparison of the most popular {industry} tools.",
        "comparison", frozenset({"industry"})),
    PromptTemplate(
        "What are the pros and cons of the leading {industry} products?",
        "comparison", frozenset({"industry"})),
]

# Alternatives — "what else should I consider" (surfaces competitor sets)
ALTERNATIVES = [
    PromptTemplate(
        "What are some good alternatives to the market leader in {industry}?",
        "alternatives", frozenset({"industry"})),
    PromptTemplate(
        "Which up-and-coming {industry} tools should I look at?",
        "alternatives", frozenset({"industry"})),
    PromptTemplate(
        "What are the best indie or newer {industry} platforms?",
        "alternatives", frozenset({"industry"})),
]

# Use-case — "I need to do X, what tool should I use"
USE_CASE = [
    PromptTemplate(
        "I need to {use_case}. What tools should I consider?",
        "use_case", frozenset({"use_case"})),
    PromptTemplate(
        "What's the best {industry} platform for {use_case}?",
        "use_case", frozenset({"industry", "use_case"})),
    PromptTemplate(
        "Can you recommend a {industry} solution that helps with {use_case}?",
        "use_case", frozenset({"industry", "use_case"})),
]

# Category — "what even is this space" (low-funnel education queries)
CATEGORY = [
    PromptTemplate(
        "I'm new to {industry}. What are the main tools I should know about?",
        "category", frozenset({"industry"})),
    PromptTemplate(
        "What categories of {industry} software exist and which are the top vendors in each?",
        "category", frozenset({"industry"})),
]

# Local — region/market scoped (only used when a location is set)
LOCAL = [
    PromptTemplate(
        "What are the best {industry} tools in {location}?",
        "local", frozenset({"industry", "location"})),
    PromptTemplate(
        "Which {industry} platforms do businesses in {location} use most?",
        "local", frozenset({"industry", "location"})),
]

# Persona — bias toward specific buyer shapes
PERSONA = [
    PromptTemplate(
        "What {industry} tool would you recommend for a 5-person startup?",
        "persona", frozenset({"industry"})),
    PromptTemplate(
        "What {industry} platform is best for a mid-market company (50-200 employees)?",
        "persona", frozenset({"industry"})),
    PromptTemplate(
        "Which {industry} solution is best for enterprise teams with strict security requirements?",
        "persona", frozenset({"industry"})),
]

# Review-style — surfaces sentiment and third-party citations
REVIEW = [
    PromptTemplate(
        "What do users say are the pros and cons of the top {industry} tools?",
        "review", frozenset({"industry"})),
    PromptTemplate(
        "Which {industry} products have the best reputation among reviewers?",
        "review", frozenset({"industry"})),
]

# The master set. Each entry carries its intent so the UI can group / weight.
ALL_TEMPLATES: tuple = (
    *RECOMMENDATION,
    *COMPARISON,
    *ALTERNATIVES,
    *USE_CASE,
    *CATEGORY,
    *PERSONA,
    *REVIEW,
)


def _dedupe_preserving_order(items: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


class PromptLibrary:
    """
    Generates an intent-balanced prompt set for an audit.

    The default mix samples across all intents so no single query shape
    dominates the benchmark. Capped at `max_prompts` so API cost stays
    bounded.
    """

    DEFAULT_MAX = 10

    @classmethod
    def generate(
        cls,
        *,
        industry: str,
        use_case: str = "",
        location: str = "",
        max_prompts: int = DEFAULT_MAX,
    ) -> list[dict]:
        """Return a list of {"text": str, "intent": str} dicts.

        We return dicts (not bare strings) so callers can surface intents
        to the UI without re-classifying. Existing callers that only need
        strings can map `p["text"] for p in generate(...)`.
        """
        industry_norm = (industry or "software").strip()
        use_case_norm = (use_case or industry_norm).strip()
        location_norm = (location or "").strip()

        # Intent weighting: we take the first N from each set to keep a balanced
        # mix even when max_prompts is small. Recommendation and comparison
        # are load-bearing (highest intent-to-mention signal), so they get more.
        priority_order: list[tuple[tuple[PromptTemplate, ...], int]] = [
            (tuple(RECOMMENDATION), 2),  # take 2 recommendation prompts
            (tuple(COMPARISON),     2),
            (tuple(USE_CASE),       2),
            (tuple(ALTERNATIVES),   1),
            (tuple(CATEGORY),       1),
            (tuple(PERSONA),        1),
            (tuple(REVIEW),         1),
        ]
        if location_norm:
            priority_order.insert(3, (tuple(LOCAL), 1))

        picked: list[dict] = []
        seen_texts: set = set()

        for bucket, take_n in priority_order:
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
                picked.append({"text": text, "intent": template.intent})
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
    ) -> list[str]:
        """Convenience wrapper for callers that only need the text list."""
        return [
            p["text"] for p in cls.generate(
                industry=industry,
                use_case=use_case,
                location=location,
                max_prompts=max_prompts,
            )
        ]

    @classmethod
    def intents_for(cls, prompt_texts: Iterable[str]) -> list[str]:
        """Best-effort lookup of intent tags for arbitrary prompt strings.

        Useful when the audit stored prompts as bare strings (backward compat)
        and the UI wants to show an intent chip next to each one.
        """
        index: dict[str, str] = {}
        for t in ALL_TEMPLATES:
            # Match the frozen template text form; substitutions won't be exact,
            # so we also index on a lowered, placeholder-stripped key.
            normalized = t.text.lower()
            for ph in t.placeholders:
                normalized = normalized.replace("{" + ph + "}", "")
            index[normalized.strip()] = t.intent
        out = []
        for text in prompt_texts:
            lower = text.strip().lower()
            matched = "custom"
            for key, intent in index.items():
                if key and key in lower:
                    matched = intent
                    break
            out.append(matched)
        return out
