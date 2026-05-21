"""Resolve template variables for a (website, prompt) pair.

Composition order (later wins for the *user-managed* dict so customers
can override our auto-derived defaults):

  1. Auto-derived from the website (company_name / industry / location)
  2. Per-website :class:`PromptVariableSet.variables` dictionary

This means out of the box every customer gets sensible substitutions
without filling in their dictionary, but any value they explicitly set
in the panel takes precedence.
"""
from __future__ import annotations

from apps.prompt_library.models import Prompt
from apps.prompt_library.services.template_parser import (
    extract_variables,
    fill_template,
)


def _auto_variables(website) -> dict:
    """Best-effort defaults pulled directly off the Website model."""
    if website is None:
        return {}
    out: dict = {}
    name = getattr(website, "name", "") or ""
    if name:
        out["company_name"] = name
        out["brand"] = name
    industry = getattr(website, "industry", "") or ""
    if industry:
        out["industry"] = industry
    # Location: try a few common shapes without hard-coding our own model.
    locations = getattr(website, "locations", None)
    if locations:
        try:
            first = locations[0] if isinstance(locations, (list, tuple)) else None
            if first:
                if isinstance(first, dict):
                    loc = first.get("city") or first.get("name") or ""
                else:
                    loc = str(first)
                if loc:
                    out["location"] = loc
        except Exception:
            pass
    return out


def _user_variables(website) -> dict:
    if website is None:
        return {}
    try:
        var_set = getattr(website, "prompt_variables", None)
        if var_set is None:
            return {}
        return dict(var_set.variables or {})
    except Exception:
        return {}


def resolve_variables(website) -> dict:
    """Merged variable dict: auto-derived plus the website's user dict."""
    merged = _auto_variables(website)
    merged.update(_user_variables(website))
    return merged


def resolve_for_website(website, prompt: Prompt) -> tuple[str, list[str]]:
    """Return ``(filled_template, missing_var_list)`` for the prompt.

    Falls back to ``prompt.text`` when the prompt has no template body so
    legacy prompts continue to render. Always tolerant of missing
    variables — placeholders are left in place and reported as missing.
    """
    body = (prompt.template_text or "").strip() or (prompt.text or "")
    variables = resolve_variables(website)
    return fill_template(body, variables, strict=False)


def variables_with_provenance(website) -> list[dict]:
    """Return [{name, value, source}] for the variables panel UI.

    ``source`` is ``"auto"`` for values derived from the Website model
    and ``"user"`` for values from the per-website dictionary. User
    entries override auto entries with the same key.
    """
    auto = _auto_variables(website)
    user = _user_variables(website)
    rows: list[dict] = []
    for key, value in auto.items():
        rows.append({
            "name": key,
            "value": user.get(key, value),
            "source": "user" if key in user else "auto",
        })
    for key, value in user.items():
        if key in auto:
            continue
        rows.append({"name": key, "value": value, "source": "user"})
    return rows


def sync_template_variables(prompt: Prompt) -> list[str]:
    """Refresh ``prompt.template_variables`` from the current template.

    Returns the new variable list. Saves the prompt only when the list
    actually changes so we don't churn ``updated_at`` for no reason.
    """
    body = prompt.template_text or ""
    found = extract_variables(body)
    if list(prompt.template_variables or []) != found:
        prompt.template_variables = found
        prompt.save(update_fields=["template_variables", "updated_at"])
    return found
