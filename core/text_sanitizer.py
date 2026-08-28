"""Sanitization for untrusted text before it enters an LLM prompt.

Cansee crawls third-party web pages and search results and feeds the text
to LLMs. That text is attacker-influenceable, so it is an indirect
prompt-injection vector (OWASP LLM01). This module strips the classes of
characters used to hide or smuggle instructions, and provides a cheap
heuristic to flag likely injection attempts.

This is defense-in-depth alongside structural isolation at the prompt layer
(see apps.llm_ranking.services.ranking_service.build_enriched_system_prompt),
not a replacement for it. Treat all crawled content as data, never
instructions.
"""
from __future__ import annotations

import re
import unicodedata

# Characters that let hidden or misleading instructions ride along in
# otherwise-innocent text. Defined by escape only (no literal control chars
# in the source). Stripped before the text reaches a prompt:
#   - C0/C1 control chars, except \t (\x09) and \n (\x0a) which we keep
#   - zero-width space/joiner/non-joiner, word joiner, BOM, soft hyphen
#   - bidirectional overrides/isolates (used to visually reorder text)
#   - the Unicode "tag" block (an ASCII-smuggling channel)
_STRIP_RE = re.compile(
    "["
    "\x00-\x08\x0b-\x1f\x7f-\x9f"          # controls, keeping \t and \n
    "​-‍⁠﻿­"       # zero-width + soft hyphen
    "‪-‮⁦-⁩"            # bidi overrides / isolates
    "\U000e0000-\U000e007f"                 # Unicode tag block
    "]"
)

_WS_RUN_RE = re.compile(r"[ \t]{3,}")
_NEWLINE_RUN_RE = re.compile(r"\n{4,}")

# Cheap signals that a chunk of crawled text is trying to talk to the model
# rather than describe a business. Not exhaustive — a flag, not a gate.
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above)", re.I),
    re.compile(r"\byou\s+are\s+now\b", re.I),
    re.compile(r"\bsystem\s+prompt\b", re.I),
    re.compile(r"\bnew\s+instructions?\b", re.I),
    re.compile(r"</?\s*(?:system|assistant|user)\s*>", re.I),
    re.compile(r"\b(?:BEGIN|END)\s+(?:SYSTEM|PROMPT)\b", re.I),
]


def sanitize_untrusted_text(text: str, *, max_len: int | None = None) -> str:
    """Return ``text`` with hidden/smuggling characters removed and whitespace
    collapsed. NFKC-normalizes so look-alike/compatibility forms can't dodge
    the pattern checks downstream. Always returns a string.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = _STRIP_RE.sub("", text)
    text = _WS_RUN_RE.sub("  ", text)
    text = _NEWLINE_RUN_RE.sub("\n\n\n", text)
    text = text.strip()
    if max_len is not None and len(text) > max_len:
        text = text[:max_len]
    return text


def detect_injection(text: str) -> float:
    """Return a rough 0..1 confidence that ``text`` contains prompt-injection
    content. Cheap and pattern-based; intended for flag-and-quarantine
    (e.g. skip RAG ingest on a high score), not hard blocking.
    """
    if not text:
        return 0.0
    hits = sum(1 for pat in _INJECTION_PATTERNS if pat.search(text))
    # A single strong marker is already suspicious; saturate quickly.
    return min(1.0, hits / 2.0)
