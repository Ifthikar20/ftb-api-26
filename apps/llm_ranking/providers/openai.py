"""OpenAI GPT provider."""
from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class OpenAIProvider(LLMProvider):
    name = "gpt4"
    model = "gpt-4o-mini"
    api_key_setting = "OPENAI_API_KEY"

    def _call(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        import openai

        client = openai.OpenAI(api_key=self.api_key)
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
