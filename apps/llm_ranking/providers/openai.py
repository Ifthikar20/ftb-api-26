"""OpenAI GPT provider."""
from django.conf import settings

from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class OpenAIProvider(LLMProvider):
    name = "gpt4"
    model = "gpt-4o-mini"
    api_key_setting = "OPENAI_API_KEY"
    # OpenAI Tier 1 for gpt-4o-mini = ~500 RPM. Cap at 200 for headroom.
    rpm = 200
    burst = 30

    def _call(self, *, prompt: str, system_prompt: str,
              region: str = "") -> ProviderResult:
        import openai

        client = openai.OpenAI(api_key=self.api_key)

        if getattr(settings, "LLM_WEBSEARCH_ENABLED", False):
            result = self._web_search_call(client, prompt, system_prompt, region)
            if result is not None:
                return result

        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt or DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        usage = getattr(resp, "usage", None)
        return ProviderResult(
            succeeded=True,
            text=resp.choices[0].message.content.strip(),
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )

    def _web_search_call(self, client, prompt, system_prompt, region):
        """Try the Responses API with the web_search tool + user_location.

        Returns a ProviderResult, or None to signal the caller to fall back
        to a plain chat completion (older SDK, tool unavailable, etc.).
        """
        from apps.llm_ranking.services.regions import get_region

        try:
            tool: dict = {"type": "web_search_preview"}
            country = get_region(region).perplexity_country if region else ""
            if country:
                tool["user_location"] = {"type": "approximate", "country": country}
            resp = client.responses.create(
                model=self.model,
                instructions=system_prompt or DEFAULT_SYSTEM,
                input=prompt,
                tools=[tool],
                max_output_tokens=1024,
            )
            usage = getattr(resp, "usage", None)
            return ProviderResult(
                succeeded=True,
                text=(getattr(resp, "output_text", "") or "").strip(),
                input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            )
        except Exception:
            return None
