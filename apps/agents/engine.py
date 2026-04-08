"""
Agent Engine
────────────
The core observe→think→act loop. Given an AgentRun, the engine:
1. Builds context from previous steps + agent type config
2. Asks Claude what to do next (which tool to call, or DONE/NEEDS_APPROVAL)
3. Executes the tool and records the result
4. Loops until done, paused, or max steps reached
"""
import json
import logging
import time

from django.conf import settings
from django.utils import timezone

from apps.agents.agent_types import get_agent_config
from apps.agents.models import AgentRun, AgentStep
from apps.agents.tools import TOOL_REGISTRY, execute_tool

logger = logging.getLogger("apps.agents")


class AgentEngine:
    """Runs a multi-step AI agent loop."""

    def run(self, agent_run: AgentRun) -> AgentRun:
        """Execute the agent loop for the given run."""
        config = get_agent_config(agent_run.agent_type)
        max_steps = config["max_steps"]

        # Mark as running
        agent_run.status = "running"
        agent_run.started_at = timezone.now()
        agent_run.save(update_fields=["status", "started_at", "updated_at"])

        website_id = str(agent_run.website_id)

        try:
            for step_num in range(max_steps):
                # 1. Build context
                context = self._build_context(agent_run, config, website_id)

                # 2. Ask Claude for next action
                start = time.time()
                decision = self._plan_next_step(context, config)
                planning_ms = int((time.time() - start) * 1000)

                tokens = decision.get("_tokens_used", 0)
                agent_run.total_tokens += tokens

                action = decision.get("action", "DONE")

                # 3. Handle DONE
                if action == "DONE":
                    agent_run.summary = decision.get("summary", "Agent completed successfully.")
                    agent_run.findings = decision.get("findings", [])
                    agent_run.status = "completed"
                    agent_run.completed_at = timezone.now()
                    if agent_run.started_at:
                        agent_run.duration_ms = int(
                            (agent_run.completed_at - agent_run.started_at).total_seconds() * 1000
                        )
                    agent_run.save()
                    logger.info(f"Agent {agent_run.id} completed in {agent_run.steps_count} steps")
                    return agent_run

                # 4. Handle NEEDS_APPROVAL
                if action == "NEEDS_APPROVAL":
                    agent_run.status = "paused"
                    agent_run.approval_request = decision.get("approval_request", "")
                    agent_run.context["pending_actions"] = decision.get("pending_actions", [])
                    agent_run.save()
                    logger.info(f"Agent {agent_run.id} paused for approval at step {step_num}")
                    return agent_run

                # 5. Execute tool
                tool_name = decision.get("tool", "")
                tool_params = decision.get("params", {})
                reasoning = decision.get("reasoning", "")

                # Inject website_id if the tool needs it
                if "website_id" in TOOL_REGISTRY.get(tool_name, {}).get("params", {}):
                    tool_params["website_id"] = website_id

                # Validate tool is allowed
                if tool_name not in config["allowed_tools"]:
                    logger.warning(f"Agent tried to use disallowed tool: {tool_name}")
                    AgentStep.objects.create(
                        agent_run=agent_run,
                        step_number=step_num,
                        reasoning=reasoning,
                        tool_name=tool_name,
                        tool_params=tool_params,
                        tool_result={"error": f"Tool '{tool_name}' is not allowed for this agent type"},
                        status="skipped",
                        tokens_used=tokens,
                        duration_ms=planning_ms,
                    )
                    agent_run.steps_count += 1
                    agent_run.save(update_fields=["steps_count", "total_tokens", "updated_at"])
                    continue

                # Execute
                exec_start = time.time()
                result = execute_tool(tool_name, tool_params)
                exec_ms = int((time.time() - exec_start) * 1000)

                step_status = "completed" if result.get("success") else "failed"

                # Record step
                AgentStep.objects.create(
                    agent_run=agent_run,
                    step_number=step_num,
                    reasoning=reasoning,
                    tool_name=tool_name,
                    tool_params=tool_params,
                    tool_result=self._truncate_result(result),
                    status=step_status,
                    tokens_used=tokens,
                    duration_ms=planning_ms + exec_ms,
                )

                agent_run.steps_count += 1

                # Store tool result in context for next iteration
                agent_run.context[f"step_{step_num}_result"] = {
                    "tool": tool_name,
                    "success": result.get("success"),
                    "data_summary": self._summarize_data(result.get("data")),
                }
                agent_run.save(update_fields=["steps_count", "total_tokens", "context", "updated_at"])

            # Max steps reached — wrap up
            agent_run.summary = "Agent reached maximum steps. Review the findings below."
            agent_run.status = "completed"
            agent_run.completed_at = timezone.now()
            if agent_run.started_at:
                agent_run.duration_ms = int(
                    (agent_run.completed_at - agent_run.started_at).total_seconds() * 1000
                )
            agent_run.save()
            return agent_run

        except Exception as e:
            logger.error(f"Agent {agent_run.id} failed: {e}")
            agent_run.status = "failed"
            agent_run.error_message = str(e)[:2000]
            agent_run.completed_at = timezone.now()
            agent_run.save()
            return agent_run

    def resume(self, agent_run: AgentRun) -> AgentRun:
        """Resume a paused agent after approval."""
        if agent_run.status != "paused":
            raise ValueError("Agent is not paused")

        # Execute any pending actions
        pending = agent_run.context.pop("pending_actions", [])
        config = get_agent_config(agent_run.agent_type)
        website_id = str(agent_run.website_id)

        agent_run.status = "running"
        agent_run.approved_at = timezone.now()
        agent_run.save(update_fields=["status", "approved_at", "context", "updated_at"])

        for _i, pa in enumerate(pending):
            tool_name = pa.get("tool", "")
            tool_params = pa.get("params", {})
            if "website_id" in TOOL_REGISTRY.get(tool_name, {}).get("params", {}):
                tool_params["website_id"] = website_id

            if tool_name in config["allowed_tools"]:
                result = execute_tool(tool_name, tool_params)
                AgentStep.objects.create(
                    agent_run=agent_run,
                    step_number=agent_run.steps_count,
                    reasoning=f"Approved action: {pa.get('reasoning', '')}",
                    tool_name=tool_name,
                    tool_params=tool_params,
                    tool_result=self._truncate_result(result),
                    status="completed" if result.get("success") else "failed",
                )
                agent_run.steps_count += 1

        agent_run.status = "completed"
        agent_run.completed_at = timezone.now()
        agent_run.summary = f"Campaign approved and {len(pending)} action(s) executed."
        agent_run.save()
        return agent_run

    # ── Private helpers ──

    def _build_context(self, agent_run: AgentRun, config: dict, website_id: str) -> dict:
        """Build the full context for the AI planner."""
        # Gather previous step results
        previous_steps = []
        for step in agent_run.steps.order_by("step_number"):
            previous_steps.append({
                "step": step.step_number,
                "tool": step.tool_name,
                "status": step.status,
                "result_summary": step.tool_result.get("data_summary")
                    if isinstance(step.tool_result, dict)
                    else str(step.tool_result)[:500],
            })

        return {
            "website_id": website_id,
            "website_name": agent_run.website.name,
            "website_url": agent_run.website.url,
            "website_industry": getattr(agent_run.website, "industry", "") or "general",
            "agent_type": agent_run.agent_type,
            "steps_completed": len(previous_steps),
            "max_steps": config["max_steps"],
            "previous_steps": previous_steps,
            "accumulated_context": {
                k: v for k, v in agent_run.context.items()
                if not k.startswith("_")
            },
        }

    def _plan_next_step(self, context: dict, config: dict) -> dict:
        """Ask Claude to decide the next action."""
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Build available tools list
        allowed = config["allowed_tools"]
        tools_desc = []
        for name in allowed:
            tool = TOOL_REGISTRY.get(name)
            if tool:
                params_desc = ", ".join(
                    f"{k} ({v.get('type', 'string')}, {'required' if v.get('required') else 'optional'})"
                    for k, v in tool["params"].items()
                    if k != "website_id"  # auto-injected
                )
                tools_desc.append(f"  - {name}: {tool['description']}. Params: {params_desc or 'none'}")

        tools_text = "\n".join(tools_desc)

        user_prompt = f"""Current context:
{json.dumps(context, indent=2, default=str)}

Available tools:
{tools_text}

Based on the context and previous steps, decide what to do next.

Return a JSON object with ONE of these structures:

1. To call a tool:
{{"action": "CALL_TOOL", "tool": "tool_name", "params": {{}}, "reasoning": "why this step"}}

2. To finish (when you have enough data to provide a summary):
{{"action": "DONE", "summary": "what you found", "findings": [{{"title": "...", "description": "...", "impact": "high|medium|low", "action": "what to do"}}]}}

3. To request human approval (for actions that modify data like scheduling content):
{{"action": "NEEDS_APPROVAL", "approval_request": "what you want to do and why", "pending_actions": [{{"tool": "...", "params": {{}}, "reasoning": "..."}}]}}

Rules:
- Do NOT call a tool you already called with the same params (check previous_steps)
- website_id is auto-injected, do NOT include it in params
- If you have gathered enough data, output DONE with findings
- Only request approval for data-modifying actions (generate_content_brief)

Return ONLY valid JSON, no markdown."""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=config["system_prompt"],
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = {"action": "DONE", "summary": text[:500], "findings": []}

        result["_tokens_used"] = tokens_used
        return result

    def _truncate_result(self, result: dict, max_size: int = 5000) -> dict:
        """Truncate tool results to avoid bloating the database."""
        serialized = json.dumps(result, default=str)
        if len(serialized) > max_size:
            return {
                "success": result.get("success"),
                "data_summary": self._summarize_data(result.get("data")),
                "truncated": True,
            }
        return result

    def _summarize_data(self, data, max_items: int = 5) -> str:
        """Create a brief summary of tool result data."""
        if data is None:
            return "No data returned"
        if isinstance(data, str):
            return data[:300]
        if isinstance(data, list):
            count = len(data)
            preview = data[:max_items]
            return f"{count} items. First {min(count, max_items)}: {json.dumps(preview, default=str)[:500]}"
        if isinstance(data, dict):
            keys = list(data.keys())[:10]
            return f"Dict with keys: {keys}. Preview: {json.dumps(data, default=str)[:500]}"
        return str(data)[:300]
