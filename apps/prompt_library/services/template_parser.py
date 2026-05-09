"""Parse and fill `{{ variable }}` placeholders in prompt templates.

The template syntax intentionally mirrors a tiny subset of Jinja so
authors can copy-paste between docs and the editor without surprises.
Only bare identifier substitution is supported — no filters, blocks,
or expressions, which keeps parsing trivially safe.
"""
from __future__ import annotations

import re

VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def extract_variables(template_text: str) -> list[str]:
    """Return ordered list of unique variable names found in template."""
    if not template_text:
        return []
    seen: list[str] = []
    for m in VARIABLE_PATTERN.finditer(template_text):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def fill_template(
    template_text: str,
    variables: dict,
    *,
    strict: bool = False,
) -> tuple[str, list[str]]:
    """Replace ``{{ x }}`` with ``variables[x]``.

    Returns ``(filled_text, missing_var_list)``. If ``strict`` is True,
    raises ``ValueError`` on missing variables. Otherwise leaves the
    placeholder in place and adds the var name to the missing list.
    """
    if not template_text:
        return "", []

    missing: list[str] = []
    variables = variables or {}

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        if name in variables and variables[name] not in (None, ""):
            return str(variables[name])
        if name not in missing:
            missing.append(name)
        return match.group(0)

    filled = VARIABLE_PATTERN.sub(_replace, template_text)
    if strict and missing:
        raise ValueError(f"Missing template variables: {missing}")
    return filled, missing


def has_unfilled_variables(text: str) -> bool:
    """True when the text still contains ``{{ var }}`` placeholders."""
    if not text:
        return False
    return bool(VARIABLE_PATTERN.search(text))
