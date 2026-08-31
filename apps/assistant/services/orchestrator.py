"""Single-turn orchestration for the Ask Cansee assistant.

Grounds every answer in (1) the deterministic per-tenant fact block and
(2) RAG retrieval over the tenant's unified knowledge corpus, then makes
one metered, spend-walled LLM call. Tenant scope is carried by the
(user, website) pair the caller resolved through TenantScopedAPIView —
this module never reads an identifier off the request body.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")

# Max conversation turns from the client folded into the prompt.
_MAX_HISTORY_TURNS = 8
# Guard the prompt against a runaway pasted history.
_MAX_HISTORY_CHARS = 6000

_SYSTEM_PROMPT = (
    "You are Cansee, the user's AI growth and visibility assistant. You "
    "can see their real account data across the whole product: traffic and "
    "analytics, AI-search visibility across ChatGPT/Claude/Gemini/"
    "Perplexity, per-prompt performance, the saved prompt library, Google "
    "Search Console queries, brand-security findings, citations and source "
    "influence, audit history, content briefs, agent insights, the "
    "knowledge base, and AI usage.\n\n"
    "Rules:\n"
    "- Answer from the LIVE ACCOUNT FACTS and the retrieved KNOWLEDGE BASE "
    "context in the prompt. These are the user's real data.\n"
    "- Never fabricate numbers. If the data needed to answer is not present, "
    "say plainly what is not tracked and point to the Cansee page that has "
    "it (Analytics, AI Visibility, Brand Security, Prompt Library, Billing).\n"
    "- Be concise and helpful. Format your reply in clean GitHub-flavored "
    "Markdown: short paragraphs, **bold** for key figures, bullet lists, and "
    "compact tables when comparing things. Do not wrap the whole reply in a "
    "code block.\n"
    "- Write in a friendly, direct voice. Lead with the answer, then the "
    "supporting detail.\n"
    "- When you compare quantities across several things (brands, prompts, "
    "providers, pages) or show a value over time, ALSO emit one chart so "
    "the shape is visible at a glance. Use a fenced block tagged `chart` "
    "containing only JSON, on its own lines:\n"
    "```chart\n"
    '{"type": "bar", "title": "AI visibility by brand", "unit": "%", '
    '"labels": ["You", "Brex", "PayPal"], '
    '"datasets": [{"label": "Visibility", "data": [6.3, 15.5, 15.5]}]}\n'
    "```\n"
    "  type is bar, line or doughnut. At most 8 labels and 3 datasets. Use "
    "only numbers that appear in the facts above -- never invent a series "
    "to make a chart. Put the chart beside the prose that explains it, "
    "never instead of it, and at most two charts per reply."
)


def _format_history(history) -> str:
    if not history:
        return ""
    turns = []
    for turn in list(history)[-_MAX_HISTORY_TURNS:]:
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        speaker = "User" if role == "user" else "Cansee"
        turns.append(f"{speaker}: {content}")
    if not turns:
        return ""
    block = "Conversation so far:\n" + "\n".join(turns)
    return block[-_MAX_HISTORY_CHARS:]


def answer(*, user, website, question, history=None) -> dict:
    """Answer a free-form question for one (user, website). Returns
    {"answer": str, "grounded": bool}. Never raises for expected failure
    modes (no provider, empty model reply)."""
    question = (question or "").strip()
    if not question:
        return {
            "answer": "Ask me anything about your traffic, AI visibility, "
                      "brand security, or saved prompts.",
            "grounded": False,
            "provider": "",
            "model": "",
        }

    from apps.assistant.services.context_builder import build_fact_block

    # The question drives which product areas get loaded (prompt metrics,
    # Search Console, citations, audits, content, agents...).
    facts = build_fact_block(user, website, question=question)

    context = ""
    try:
        from apps.rag.services.retriever import retrieve_context_block

        context = retrieve_context_block(
            user=user, website=website, query=question,
            top_k=5, max_chars=3000,
        ) or ""
    except Exception:
        context = ""

    from apps.llm_ranking.providers import get_provider, get_synthesis_provider

    provider = get_provider("claude") or get_synthesis_provider()
    if provider is None:
        return {
            "answer": "No AI provider is configured yet, so I can't answer "
                      "questions. Add an AI provider key in Settings.",
            "grounded": False,
            "provider": "",
            "model": "",
        }

    convo = _format_history(history)
    prompt = (
        (f"{facts}\n\n" if facts else "")
        + (f"{context}\n\n" if context else "")
        + (f"{convo}\n\n" if convo else "")
        + f"User question: {question}\n\n"
        "Answer in Markdown."
    )

    result = provider.query(
        prompt, _SYSTEM_PROMPT,
        user=user, website=website,
        audit_id=f"assistant:{website.id}",
        role="assistant_chat", module="assistant",
    )
    text = (getattr(result, "text", "") or "").strip()
    if not text:
        text = ("I couldn't generate an answer just now. Please try again in "
                "a moment.")
    return {
        "answer": text,
        # True when the model was handed this tenant's own data -- the fact
        # block, retrieved context, or both. It says the answer was written
        # WITH those numbers in front of it; it does not verify that the
        # answer used them correctly. The UI wording has to match that.
        "grounded": bool(facts or context),
        # Which model actually answered. `get_provider("claude")` is the
        # preference but the synthesis fallback can substitute another, so
        # this is read off the provider that ran rather than assumed.
        "provider": getattr(provider, "name", "") or "",
        "model": getattr(provider, "model", "") or "",
    }
