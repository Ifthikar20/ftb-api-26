"""Prompt-source dispatcher for LLM ranking audits.

The legacy code path generates prompts inline inside
:class:`LLMRankingService` and stores them on the audit's ``prompts``
JSON field. This module wraps that with a small switch so a caller can
choose to draw prompts from the demand-side library, the user's vault,
or both. It is intentionally pure-Python — no DB writes — so it can be
called from the API layer before the audit task is enqueued.
"""
from __future__ import annotations

from collections.abc import Iterable


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
