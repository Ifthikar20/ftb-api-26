"""
Base contract for LLM providers used by the ranking module.

Subclasses implement only `_call()` (the SDK quirks). The base handles:
  - duration measurement
  - centralized token/cost recording via core.ai_tracking.record_usage
  - error envelope normalisation
so adding a new provider can never silently skip cost tracking again.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("apps")


@dataclass
class ProviderResult:
    """Uniform envelope returned by every LLMProvider.query() call."""

    succeeded: bool
    text: str = ""
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    raw: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMProvider:
    """Abstract base. Subclasses set name/model/api_key_setting and implement _call()."""

    # Audit-side key used in LLMRankingResult.provider and PROVIDERS registry.
    name: str = ""
    # Concrete model identifier sent to the SDK and stored in AITokenUsage.
    model: str = ""
    # Django settings attribute holding the API key for this provider.
    api_key_setting: str = ""
    # Default per-call timeout. Subclasses may override.
    timeout_seconds: int = 30

    def __init__(self):
        from django.conf import settings
        self.api_key = getattr(settings, self.api_key_setting, "") if self.api_key_setting else ""

    def is_configured(self) -> bool:
        """True when the API key is present and the SDK can be imported."""
        return bool(self.api_key)

    def query(
        self,
        prompt: str,
        system_prompt: str = "",
        *,
        user=None,
        website=None,
        audit_id: str | None = None,
        role: str = "upstream",
    ) -> ProviderResult:
        """
        Run a single prompt against the provider.

        Records token usage centrally on success. On failure returns a
        ProviderResult with succeeded=False and the upstream error string —
        callers should check `.succeeded` rather than catching exceptions.
        """
        if not self.is_configured():
            return ProviderResult(
                succeeded=False,
                error=f"{self.api_key_setting or self.name} not configured",
            )

        t0 = time.monotonic()
        try:
            result = self._call(prompt=prompt, system_prompt=system_prompt)
        except Exception as exc:  # noqa: BLE001 — providers throw a wide variety
            duration_ms = int((time.monotonic() - t0) * 1000)
            logger.warning("Provider %s call failed: %s", self.name, exc)
            return ProviderResult(succeeded=False, error=str(exc), duration_ms=duration_ms)

        result.duration_ms = int((time.monotonic() - t0) * 1000)

        if result.succeeded and (result.input_tokens or result.output_tokens):
            self._record(
                result=result, user=user, website=website,
                audit_id=audit_id, role=role,
            )
        return result

    # ── To implement in subclasses ────────────────────────────────────────

    def _call(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        raise NotImplementedError

    # ── Centralised cost recording ────────────────────────────────────────

    def _record(self, *, result, user, website, audit_id, role):
        try:
            from core.ai_tracking import record_usage
            metadata = {"role": role}
            if audit_id:
                metadata["audit_id"] = str(audit_id)
            record_usage(
                module="llm_ranking",
                model_name=self.model,
                provider=self._provider_label(),
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                user=user,
                website=website,
                duration_ms=result.duration_ms,
                metadata=metadata,
            )
        except Exception as exc:  # never let bookkeeping break a query
            logger.warning("record_usage failed for %s: %s", self.name, exc)

    def _provider_label(self) -> str:
        """Map audit-side key to AITokenUsage.provider value."""
        return {
            "claude": "anthropic",
            "gpt4": "openai",
            "gemini": "google",
            "perplexity": "perplexity",
        }.get(self.name, self.name)
