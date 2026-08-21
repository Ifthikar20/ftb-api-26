"""Query the LLM providers for what they say about our brand."""
from __future__ import annotations

import logging

logger = logging.getLogger("apps")


def ask_all_providers(prompt: str, *, user=None, website=None) -> list[dict]:
    """Ask every configured provider ``prompt``. Returns list of ``{model, text}``.

    Failures return an empty answer; the LLM Truth agent decides how to score
    silence vs a real reply. This never raises.

    ``user``/``website`` attribute the spend (Brand Security scans are
    system work billed to the website owner); leaving them unset would
    skip both the ledger and the spend wall.
    """
    from apps.llm_ranking.providers import PROVIDERS

    out: list[dict] = []
    for name, cls in PROVIDERS.items():
        try:
            provider = cls()
            if not provider.is_configured():
                continue
            result = provider.query(
                prompt,
                user=user,
                website=website,
                module="brand_security",
                role="security_probe",
                extra_metadata={"actor": "system"},
            )
            if result.succeeded and result.text:
                out.append({
                    "provider": name,
                    "model": provider.model,
                    "text": result.text,
                })
        except Exception as exc:
            logger.warning("LLM source '%s' failed: %s", name, exc)
    return out
