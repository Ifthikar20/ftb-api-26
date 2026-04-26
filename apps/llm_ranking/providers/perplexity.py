"""Perplexity provider (web-grounded Sonar models via REST)."""
import requests

from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class PerplexityProvider(LLMProvider):
    name = "perplexity"
    model = "llama-3.1-sonar-small-128k-online"
    api_key_setting = "PERPLEXITY_API_KEY"
    timeout_seconds = 30

    def _call(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt or DEFAULT_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1024,
            },
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        body = resp.json()
        usage = body.get("usage") or {}
        return ProviderResult(
            succeeded=True,
            text=body["choices"][0]["message"]["content"].strip(),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            raw=body,
        )
