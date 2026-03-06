import logging
from django.conf import settings
from apps.strategy.models import NicheAnalysis

logger = logging.getLogger("apps")


class NicheFinderService:
    @staticmethod
    def analyze(*, website) -> NicheAnalysis:
        """Analyze the website's niche positioning."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": f"Analyze the market niche for: {website.url} ({website.name}, industry: {website.industry or 'general'}). "
                               "Return JSON with: clusters (list of topic clusters), opportunities (keyword opportunities), "
                               "positioning (unique positioning angles). Return ONLY valid JSON."
                }],
            )

            import json
            data = json.loads(response.content[0].text)
        except Exception as e:
            logger.error(f"Niche analysis failed: {e}")
            data = {"clusters": [], "opportunities": [], "positioning": {}}

        return NicheAnalysis.objects.create(
            website=website,
            clusters=data.get("clusters", []),
            opportunities=data.get("opportunities", []),
            positioning=data.get("positioning", {}),
        )
