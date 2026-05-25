"""Google Gemini provider."""
from django.conf import settings

from .base import LLMProvider, ProviderResult
from .claude import DEFAULT_SYSTEM


class GeminiProvider(LLMProvider):
    name = "gemini"
    model = "gemini-1.5-flash"
    api_key_setting = "GEMINI_API_KEY"
    # Gemini 1.5 Flash free tier = 15 RPM. Paid tier higher; stay conservative.
    rpm = 15
    burst = 10

    def _call(self, *, prompt: str, system_prompt: str,
              region: str = "") -> ProviderResult:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        full_prompt = f"{system_prompt or DEFAULT_SYSTEM}\n\n{prompt}"

        # Gemini's grounding tool has no per-request country parameter, so the
        # geo signal here comes from the region-flavoured prompt text; enabling
        # Google Search grounding still makes the answer web-fresh.
        use_search = getattr(settings, "LLM_WEBSEARCH_ENABLED", False)
        resp = None
        if use_search:
            try:
                model = genai.GenerativeModel(self.model, tools="google_search_retrieval")
                resp = model.generate_content(full_prompt)
            except Exception:
                resp = None
        if resp is None:
            model = genai.GenerativeModel(self.model)
            resp = model.generate_content(full_prompt)

        usage = getattr(resp, "usage_metadata", None)
        return ProviderResult(
            succeeded=True,
            text=resp.text.strip(),
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
        )
