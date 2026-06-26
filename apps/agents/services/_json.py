"""Tolerant JSON-object extraction from an LLM response."""
from __future__ import annotations

import json
import re


def extract_object(text: str) -> dict:
    """Return the first JSON object found in ``text``, or {} on failure."""
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
