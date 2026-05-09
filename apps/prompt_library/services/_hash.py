"""Shared text-normalisation + hashing helpers."""
from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Lowercase, collapse whitespace, strip trailing punctuation —
    enough to fold trivial casing/spacing differences for exact dedup."""
    return _WS.sub(" ", (text or "").lower()).strip().rstrip(".?!")


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()
