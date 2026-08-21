"""Compatibility shim — the provider contract now lives in core.llm.base.

The base class is pure infrastructure (it depends only on core.resilience
and core.ai_tracking), so it moved to core where any app can import it
without creating a cross-app edge. The audit-answer provider subclasses
in this package are unchanged. New code should import from core.llm.
"""
from core.llm.base import LLMProvider, ProviderResult

__all__ = ["LLMProvider", "ProviderResult"]
