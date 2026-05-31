"""Anthropic Claude provider."""
from django.conf import settings

from .base import LLMProvider, ProviderResult

DEFAULT_SYSTEM = (
    "When listing tools, platforms, or products, please use a numbered list "
    "(1., 2., 3., etc.) and include a brief description for each. "
    "Be specific and mention actual product/company names."
)


class ClaudeProvider(LLMProvider):
    name = "claude"
    model = "claude-sonnet-4-20250514"
    api_key_setting = "ANTHROPIC_API_KEY"
    # Anthropic Tier 1 = 50 RPM. Stay well under to share with extraction.
    rpm = 40
    burst = 15

    def _call(self, *, prompt: str, system_prompt: str,
              region: str = "") -> ProviderResult:
        import anthropic

        from apps.llm_ranking.services.regions import get_region

        client = anthropic.Anthropic(api_key=self.api_key)
        kwargs = dict(
            model=self.model,
            max_tokens=1024,
            system=system_prompt or DEFAULT_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        if getattr(settings, "LLM_WEBSEARCH_ENABLED", False):
            tool: dict = {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }
            country = get_region(region).perplexity_country if region else ""
            if country:
                # Bias Anthropic's server-side web search to this geo.
                tool["user_location"] = {"type": "approximate", "country": country}
            kwargs["tools"] = [tool]

        try:
            resp = client.messages.create(**kwargs)
        except Exception:
            # Web search may be unavailable for this account/model — retry as
            # a plain completion so the scan still succeeds.
            if "tools" in kwargs:
                kwargs.pop("tools")
                resp = client.messages.create(**kwargs)
            else:
                raise

        # With web search the response holds several blocks (text + tool_use +
        # search results); concatenate the text blocks.
        text = " ".join(
            b.text for b in resp.content
            if getattr(b, "type", "") == "text" and getattr(b, "text", "")
        ).strip()
        return ProviderResult(
            succeeded=True,
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
