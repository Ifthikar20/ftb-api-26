"""Resolve a Prompt row from a literal prompt_text used in an audit.

Used at LLMRankingResult creation time to populate the optional
``source_prompt`` foreign key so we can later compute per-prompt
effectiveness signals. The lookup is best-effort:

* If the audit-side prompt text matches a Prompt's ``text`` exactly
  (after a strip), we return that prompt.
* Otherwise we also try matching against ``template_text`` for the rare
  case the runner passes a raw template through unchanged.
* Any error or absence returns ``None`` — the audit must never fail
  because of the linkage lookup.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("apps")


def resolve_source_prompt_id(prompt_text: str) -> Optional[str]:
    """Return a Prompt.id matching ``prompt_text`` exactly, or ``None``."""
    if not prompt_text:
        return None
    text = prompt_text.strip()
    if not text:
        return None
    try:
        from apps.prompt_library.models import Prompt
    except Exception:  # pragma: no cover — import-time only
        return None
    try:
        row = (
            Prompt.objects.filter(text=text)
            .only("id")
            .first()
            or Prompt.objects.filter(template_text=text).only("id").first()
        )
        return row.id if row else None
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("resolve_source_prompt_id failed: %s", exc)
        return None
