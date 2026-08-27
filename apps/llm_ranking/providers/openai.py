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
        The GA tool type is ``web_search``; ``web_search_preview`` is kept
        as a second attempt for accounts/models still on the preview alias.
        """
        from apps.llm_ranking.providers.openai_compat import (
            extract_responses_citations,
        )
        from apps.llm_ranking.services.regions import get_region

        country = get_region(region).perplexity_country if region else ""
        resp = None
        for tool_type in ("web_search", "web_search_preview"):
            tool: dict = {"type": tool_type}
            if country:
                tool["user_location"] = {"type": "approximate", "country": country}
            try:
                resp = client.responses.create(
                    model=self.model,
                    instructions=system_prompt or DEFAULT_SYSTEM,
                    input=prompt,
                    tools=[tool],
                    # Force the search: left to its own judgment gpt-4o-mini
                    # rarely browses, which would make this audit measure its
                    # training data instead of the search-augmented answer a
                    # consumer sees (and would leave the Sources panel empty).
                    tool_choice={"type": tool_type},
                    max_output_tokens=1024,
                )
                break
            except Exception:
                resp = None
        if resp is None:
            return None
        usage = getattr(resp, "usage", None)
        return ProviderResult(
            succeeded=True,
            text=(getattr(resp, "output_text", "") or "").strip(),
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            citations=extract_responses_citations(resp),
        )
