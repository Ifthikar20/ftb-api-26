"""DeepSeek provider (OpenAI-compatible chat completions endpoint).

DeepSeek is used ONLY for offline tooling — prompt synthesis,
auto-templating raw user text, and explicit user-triggered smoke tests.
It is NEVER registered in the audit-time provider routing because audit
results must come from one of the four canonical, citation-quality
providers. We keep the adapter shape identical to the other providers so
the same rate-limiting / cost-tracking plumbing applies.
"""
from __future__ import annotations

import requests

from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class DeepSeekProvider(LLMProvider):
    name = "deepseek"
    model = "deepseek-chat"
    api_key_setting = "DEEPSEEK_API_KEY"
    timeout_seconds = 60
    # DeepSeek doesn't publish hard tier limits but is generally generous.
    # Cap conservatively to keep synthesis bursts from monopolising workers.
    rpm = 60
    burst = 20

    base_url = "https://api.deepseek.com/v1"

    def _call(self, *, prompt: str, system_prompt: str,
              region: str = "") -> ProviderResult:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "stream": False,
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage") or {}
        return ProviderResult(
            succeeded=True,
            text=data["choices"][0]["message"]["content"].strip(),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            raw=data,
        )
