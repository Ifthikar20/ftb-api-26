import logging

from django.conf import settings

from apps.strategy.models import Action, Strategy
from core.exceptions import AIGenerationFailed
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")


class StrategyGenerator:
    @staticmethod
    def generate(*, website, plan_type: str = "30") -> Strategy:
        """Generate an AI growth strategy for a website."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            prompt = StrategyGenerator._build_prompt(website=website, plan_type=plan_type)

            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            content = message.content[0].text
            strategy_data = StrategyGenerator._parse_response(content)

        except Exception as e:
            logger.error(f"AI strategy generation failed: {e}")
            raise AIGenerationFailed() from e

        strategy = Strategy.objects.create(
            website=website,
            plan_type=plan_type,
            raw_response={"content": content, "model": "claude-sonnet-4-6"},
            summary=strategy_data.get("summary", ""),
        )

        # Create action items
        for _idx, action_data in enumerate(strategy_data.get("actions", [])[:20]):
            Action.objects.create(
                strategy=strategy,
                title=action_data.get("title", ""),
                description=action_data.get("description", ""),
                action_type=action_data.get("type", ""),
                estimated_impact=action_data.get("impact", "medium"),
                estimated_time_minutes=action_data.get("time_minutes"),
                week_number=action_data.get("week", 1),
                ai_reasoning=action_data.get("reasoning", ""),
            )

        audit_log("strategy.generated", action="create", resource_type="strategy", resource_id=str(strategy.id), metadata={"website_id": str(website.id), "plan_type": plan_type})
        return strategy

    @staticmethod
    def _build_prompt(*, website, plan_type: str) -> str:
        return f"""You are a growth strategy expert. Generate a {plan_type}-day growth strategy for:

Website: {website.url}
Name: {website.name}
Industry: {website.industry or "Not specified"}

Return a JSON object with:
- summary: Brief strategy overview (2-3 sentences)
- actions: List of specific action items, each with:
  - title: Short action title
  - description: Detailed description
  - type: content|seo|technical|analytics|conversion
  - impact: low|medium|high
  - time_minutes: Estimated minutes to complete
  - week: Week number (1-4 for 30d, 1-8 for 60d, 1-12 for 90d)
  - reasoning: Why this action matters

Focus on quick wins in week 1, then sustainable growth tactics.
Return ONLY valid JSON, no markdown."""

    @staticmethod
    def _parse_response(content: str) -> dict:
        import json
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"summary": content[:500], "actions": []}
