---
description: API integration patterns for FetchBot external services (Anthropic, Google, Stripe, SendGrid). Apply when adding or modifying third-party API integrations.
---

# FetchBot API Integration Patterns

## External Service Configuration

All API keys are stored as environment variables in `.env` and loaded in `config/settings/base.py`:

| Service | Env Variable | Purpose |
|---------|-------------|---------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | AI prompts and lead parsing |
| Google Custom Search | `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID` | LinkedIn/Twitter profile discovery for leads |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Billing, subscriptions |
| SendGrid | `SENDGRID_API_KEY` | Transactional email delivery |
| DataForSEO | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | SEO/keyword data |
| Google OAuth | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | Social login |

## Adding a New API Key

1. Add to `.env`:
   ```
   NEW_SERVICE_API_KEY=your-key-here
   ```

2. Add to `.env.example` (with placeholder):
   ```
   NEW_SERVICE_API_KEY=sk-...
   ```

3. Load in `config/settings/base.py`:
   ```python
   NEW_SERVICE_API_KEY = env("NEW_SERVICE_API_KEY", default="")
   ```

4. Access in services:
   ```python
   from django.conf import settings
   api_key = settings.NEW_SERVICE_API_KEY
   ```

## AI Integration Pattern (Anthropic/Claude)

```python
import anthropic
from django.conf import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
resp = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=512,
    messages=[{"role": "user", "content": prompt}],
)
text = resp.content[0].text.strip()
```

Always:
- Wrap in try/except and log failures
- Use `re.search()` to extract JSON from potential markdown code blocks
- Provide fallback behavior when the API is unavailable

## Google Custom Search Pattern

Used by the AI Lead Finder to search LinkedIn/Twitter profiles:

```python
import requests

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

resp = requests.get(GOOGLE_SEARCH_URL, params={
    "key": settings.GOOGLE_SEARCH_API_KEY,
    "cx": settings.GOOGLE_SEARCH_ENGINE_ID,
    "q": f"site:linkedin.com/in {search_query}",
    "num": 5,
}, timeout=10)
```

### Setting Up Google Custom Search

To enable real LinkedIn/Twitter lead discovery (instead of AI-generated fallback):

1. Go to https://programmablesearchengine.google.com/
2. Create a new search engine -- set it to search the entire web
3. Copy the **Search Engine ID** (cx)
4. Go to https://console.cloud.google.com/ and enable the Custom Search JSON API
5. Create an API key
6. Add both to `.env`:
   ```
   GOOGLE_SEARCH_API_KEY=AIza...
   GOOGLE_SEARCH_ENGINE_ID=abc123...
   ```

Without these keys, the AI Lead Finder falls back to Claude-generated lead suggestions (no real LinkedIn data).

## Service Architecture

External API calls should be encapsulated in service classes under `apps/<app>/services/`:

```python
class ExternalService:
    @staticmethod
    def call_api(*, param1, param2):
        api_key = getattr(settings, "SERVICE_API_KEY", "")
        if not api_key:
            logger.warning("Service API key not configured")
            return fallback_response()
        
        try:
            result = make_api_call(api_key, param1, param2)
            return result
        except Exception as e:
            logger.error("API call failed: %s", e)
            return fallback_response()
```

Key principles:
- Always check if the API key is configured before making calls
- Always provide a graceful fallback when keys are missing
- Always set request timeouts
- Log warnings for missing config, errors for failures
- Never expose API keys in responses or frontend code
