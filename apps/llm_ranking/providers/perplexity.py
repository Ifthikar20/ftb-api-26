"""Perplexity provider (web-grounded Sonar models via REST)."""
import requests

from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class PerplexityProvider(LLMProvider):
    name = "perplexity"
    model = "llama-3.1-sonar-small-128k-online"
    api_key_setting = "PERPLEXITY_API_KEY"
    timeout_seconds = 30
    # Perplexity free tier = 50 RPM for Sonar small. Cap at 30 for headroom.
    rpm = 30
    burst = 10

    def _call(self, *, prompt: str, system_prompt: str,
              region: str = "") -> ProviderResult:
        from apps.llm_ranking.services.regions import get_region

        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
        }
        # Perplexity respects ``web_search_options.user_location`` and
        # biases the web grounding step toward that country. The other
        # providers ignore region entirely (their behaviour is purely
        # prompt-driven).
        region_obj = get_region(region) if region else None
        if region_obj and region_obj.perplexity_country:
            body["web_search_options"] = {
                "user_location": {"country": region_obj.perplexity_country},
            }
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
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
