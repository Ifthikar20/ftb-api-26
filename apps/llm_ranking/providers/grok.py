"""xAI Grok provider (OpenAI-compatible REST, with Live Search).

xAI's chat/completions endpoint is OpenAI-compatible and adds a
``search_parameters`` block for Live Search. We pass the audit region as a
``country`` filter on the web/news sources so Grok answers as a local user,
mirroring what Perplexity's ``user_location`` does.
"""
import requests
from django.conf import settings

from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class GrokProvider(LLMProvider):
    name = "grok"
    model = "grok-3"
    api_key_setting = "XAI_API_KEY"
    timeout_seconds = 40
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
        if getattr(settings, "LLM_WEBSEARCH_ENABLED", False):
            country = get_region(region).perplexity_country if region else ""
            geo = {"country": country} if country else {}
            body["search_parameters"] = {
                "mode": "auto",
                "sources": [{"type": "web", **geo}, {"type": "news", **geo}],
            }

        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
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
