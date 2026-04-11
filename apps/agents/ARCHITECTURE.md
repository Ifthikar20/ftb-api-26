# Agents App

## Purpose

Autonomous AI agents that analyze website data and take action on behalf of the user. Each agent follows an observe-think-act loop powered by Claude, with a tool registry that wraps existing FetchBot services.

## Architecture

```
User triggers agent (manual or scheduled)
  │
  ▼
AgentRun created (status: pending)
  │
  ▼
AgentEngine.run()
  │
  ├── 1. _build_context()    → Gather website data + previous step results
  ├── 2. _plan_next_step()   → Ask Claude which tool to call (or DONE/NEEDS_APPROVAL)
  ├── 3. execute_tool()      → Run the tool via TOOL_REGISTRY
  ├── 4. Record AgentStep    → Log reasoning, tool call, result
  └── 5. Loop until DONE, NEEDS_APPROVAL, or max steps
         │
         ▼
  AgentRun completed with summary + findings
```

## Agent Types

| Agent | Purpose | Tools | Max Steps | Approval? |
|---|---|---|---|---|
| `opportunity_finder` | Scans analytics and keywords for growth opportunities | analytics overview, top pages, keyword scores, trending, AI insights, lead summary | 6 | No |
| `campaign_runner` | Plans and schedules content campaigns from data | analytics, keywords, trending, keyword gaps, content brief generation | 10 | Yes (before scheduling) |
| `competitor_watcher` | Monitors competitor changes and recommends responses | competitor changes, keyword gaps, analytics, keyword scores | 5 | No |
| `anomaly_responder` | Investigates traffic anomalies and recommends fixes | analytics overview, top pages, AI insights, keyword scores | 4 | No |

## Models

| Model | Purpose |
|---|---|
| `AgentRun` | A single agent execution. Tracks type, status (pending/running/paused/completed/failed), trigger source, accumulated context, findings, approval workflow, and token usage. |
| `AgentStep` | One step in the loop — records the reasoning (why the agent chose this action), tool name, params, result, token usage, and duration. |

## Tool Registry (`tools.py`)

Tools are thin wrappers around existing FetchBot services. The registry maps tool names to callables:

| Tool | Wraps |
|---|---|
| `get_analytics_overview` | `AnalyticsService.get_overview()` |
| `get_top_pages` | `AnalyticsService.get_top_pages()` |
| `get_keyword_scores` | `KeywordIntelligenceService.get_scored_keywords()` |
| `get_trending_keywords` | `KeywordIntelligenceService.get_trending()` |
| `get_ai_insights` | `AIInsightsService.generate_insights()` |
| `get_competitor_changes` | `ChangeDetectionService.detect_changes()` |
| `get_keyword_gaps` | `ComparisonService.find_keyword_gaps()` |
| `get_lead_summary` | Direct Lead model query |
| `generate_content_brief` | Claude Haiku call for content planning |

## Key Design Decisions

- **Claude-powered planning** — The engine sends context + available tools to Claude (Sonnet), which returns a JSON decision: `CALL_TOOL`, `DONE`, or `NEEDS_APPROVAL`.
- **Tool sandboxing** — Each agent type has an `allowed_tools` list. If Claude tries to call a disallowed tool, the step is skipped.
- **Human-in-the-loop** — `campaign_runner` pauses and asks for approval before executing data-modifying actions. The `resume()` method continues after approval.
- **Context accumulation** — Each step's result summary is stored in `agent_run.context` so subsequent Claude calls can see what happened.
- **Result truncation** — Tool results are truncated to 5KB before persisting to avoid database bloat.

## Celery Tasks

| Task | Purpose |
|---|---|
| `run_agent_task` | Executes an AgentRun asynchronously via the engine |
| `run_scheduled_agents` | Periodic task that triggers scheduled agents for all active websites |

## Dependencies

- **Depends on:** `analytics`, `competitors`, `leads`, `websites`, `core`
- **External:** Anthropic API (Claude Sonnet for planning, Claude Haiku for content briefs)
