"""Prompt-source dispatcher for LLM ranking audits.

The legacy code path generates prompts inline inside
:class:`LLMRankingService` and stores them on the audit's ``prompts``
JSON field. This module wraps that with a small switch so a caller can
choose to draw prompts from the demand-side library, the user's vault,
or both. It is intentionally pure-Python — no DB writes — so it can be
called from the API layer before the audit task is enqueued.

``gather_saved_prompts`` is the primary source since 2026-08: audits run
exactly the prompts the user curated on the Prompts page. Nothing is
generated — an account with no saved prompts gets a refusal pointing at
the Prompts page, not an invented prompt set.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

logger = logging.getLogger("apps")


class NoSavedPromptsError(Exception):
    """Raised when a website has no saved prompts to audit."""


def gather_saved_prompts(website, user) -> list[dict]:
    """Materialise the website's saved prompt list into runner shape.

    Reads ``BrandPrompt`` rows (the Prompts-page list), fills
    ``{{ variables }}`` via the prompt-library resolver, and returns the
    dict shape the ranking runner consumes. The runner reads ``text``
    (and ``type`` cosmetically); ``prompt_id`` is carried so results can
    link ``source_prompt`` directly — variable-filled text won't
    hash-match ``Prompt.text``, so the text resolver can't do it.

    Raises ``NoSavedPromptsError`` when the list is empty. Callers turn
    that into a refusal that names the fix (add prompts), never into a
    generated substitute.
    """
    from apps.prompt_library.models import BrandPrompt
    from apps.prompt_library.services.variable_resolver import resolve_for_website
    from core.utils.constants import max_prompts_for_user

    rows = (
        BrandPrompt.objects.filter(website=website, prompt__is_active=True)
        .exclude(prompt__rejections__website=website)
        .select_related("prompt")
        .order_by("-created_at")
    )

    items: list[dict] = []
    seen: set[str] = set()
    for bp in rows:
        prompt = bp.prompt
        filled, missing = resolve_for_website(website, prompt)
        text = (filled or "").strip()
        if not text:
            continue
        if missing:
            logger.debug(
                "Saved prompt %s has unresolved variables %s", prompt.id, missing,
            )
        # Autoseed can create near-duplicate Prompt rows; one text, one run.
        key = " ".join(text.lower().split())
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "text": text,
            "type": prompt.intent_bucket or "custom",
            "prompt_id": str(prompt.id),
            "source_label": "Saved",
            "tags": list(bp.tags or []),
        })

    if not items:
        raise NoSavedPromptsError(
            f"Website {website.id} has no saved prompts to audit.",
        )

    cap = max_prompts_for_user(user)
    if len(items) > cap:
        logger.warning(
            "Saved prompt list for website %s truncated to plan cap: "
            "keeping %s most recent of %s.",
            website.id, cap, len(items),
        )
        items = items[:cap]
    return items


def _from_vault(audit) -> list[dict]:
    """Return the audit's existing vault prompts (whatever the keyword
    generator already populated). Each entry is the dict shape used by
    the ranking service: ``{"text": str, "intent": str|None, ...}``."""
    items: list[dict] = []
    for p in audit.prompts or []:
        if isinstance(p, str):
            items.append({"text": p, "intent": "custom", "source_label": "Vault"})
        elif isinstance(p, dict):
            d = dict(p)
            d.setdefault("source_label", "Vault")
            items.append(d)
    return items


def _from_library_sample(audit) -> list[dict]:
    """Return the prompts persisted on the audit's PromptSampleRun, if any.

    Lazy-imported so the prompt_library app stays optional during the
    rollout window — an audit without a sample run silently degrades to
    an empty list and the caller falls back to the vault.
    """
    try:
        from apps.prompt_library.models import PromptSampleEntry
    except Exception:
        return []
    sample_run = getattr(audit, "prompt_sample_run", None)
    if sample_run is None:
        return []
    entries = (
        PromptSampleEntry.objects.filter(sample_run=sample_run)
        .select_related("prompt")
        .order_by("rank")
    )
    out: list[dict] = []
    for entry in entries:
        prompt = entry.prompt
        out.append(
            {
                "text": prompt.text,
                "intent": prompt.intent_bucket,
                "source_label": f"Library / {prompt.get_source_display()}",
            }
        )
    return out


def gather_prompts(audit, prompt_source: str | None = None) -> list[dict]:
    """Resolve the prompt list for an audit run based on ``prompt_source``."""
    source = prompt_source or getattr(audit, "prompt_source", "vault") or "vault"
    if source == "library":
        prompts = _from_library_sample(audit)
        return prompts or _from_vault(audit)
    if source == "hybrid":
        return _from_library_sample(audit) + _from_vault(audit)
    return _from_vault(audit)


# Public alias matching the brief's naming.
_gather_prompts = gather_prompts


def apply_to_audit(audit, prompt_source: str | None = None) -> Iterable[dict]:
    """Resolve prompts and persist them onto the audit row.

    Call this immediately before enqueuing the Celery task so the audit
    ``prompts`` field has the final list — the existing pipeline reads
    from there without further changes.
    """
    items = gather_prompts(audit, prompt_source=prompt_source)
    audit.prompts = items
    return items
