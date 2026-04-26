"""Anthropic Claude provider."""
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

    def _call(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt or DEFAULT_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return ProviderResult(
            succeeded=True,
            text=resp.content[0].text.strip(),
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
