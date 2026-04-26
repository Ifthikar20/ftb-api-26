"""Google Gemini provider."""
from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class GeminiProvider(LLMProvider):
    name = "gemini"
    model = "gemini-1.5-flash"
    api_key_setting = "GEMINI_API_KEY"

    def _call(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        full_prompt = f"{system_prompt or DEFAULT_SYSTEM}\n\n{prompt}"
        resp = model.generate_content(full_prompt)
        usage = getattr(resp, "usage_metadata", None)
        return ProviderResult(
            succeeded=True,
            text=resp.text.strip(),
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
        )
