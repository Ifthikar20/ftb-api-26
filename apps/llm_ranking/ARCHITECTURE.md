# LLM Ranking App

## Purpose

Measures how prominently a business appears in AI-generated answers across major LLMs (Claude, GPT-4, Gemini, Perplexity). This is "SEO for AI" — understanding and improving your visibility when people ask AI assistants about your industry.

## Architecture

```
User triggers audit (or schedule auto-triggers)
  │
  ▼
LLMRankingAudit created (status: pending)
  │
  ▼
Celery Task (ai queue)
  │
  ├── Generate prompts from business context + keywords
  │     e.g., "What are the best [industry] services in [location]?"
  │
  ├── For each (prompt × provider):
  │     ├── Query the LLM API
  │     ├── Analyze response for business mention
  │     │     ├── is_mentioned (boolean)
  │     │     ├── mention_rank (position among listed items)
  │     │     ├── sentiment (positive/neutral/negative)
  │     │     ├── confidence_score (0-100)
  │     │     └── mention_context (snippet)
  │     └── Create LLMRankingResult
  │
  └── Compute aggregate scores
        ├── overall_score (0-100)
        ├── mention_rate (% of queries with a mention)
        └── avg_mention_rank (average position when mentioned)
```

## Models

| Model | Purpose |
|---|---|
| `LLMRankingAudit` | A single audit run. Stores business context snapshot (name, description, industry, location, keywords), prompts used, progress tracking, and aggregate scores. |
| `LLMRankingResult` | One response from one LLM for one prompt. Captures whether the business was mentioned, rank position, sentiment, confidence, and the full response text for review. |
| `LLMRankingSchedule` | Per-website periodic schedule. Stores business context, frequency (weekly/biweekly/monthly), and next_run_at for automatic audit creation via Celery Beat. |

## Providers

| Provider | LLM | Implementation |
|---|---|---|
| `claude` | Claude (Anthropic) | Anthropic API |
| `gpt4` | GPT-4 (OpenAI) | OpenAI API |
| `gemini` | Gemini (Google) | Google AI API |
| `perplexity` | Perplexity | Perplexity API |

## Key Design Decisions

- **Multi-provider coverage** — Queries the same prompts across 4 major LLMs to give a complete picture of AI visibility.
- **Business context snapshot** — The audit stores a snapshot of the business info at run time, so historical audits remain accurate even if the business details change.
- **Batch execution** — Audits run as async Celery tasks on the `ai` queue with progress tracking (`queries_completed / total_queries`).
- **Explainable scoring** — Each result includes `mention_context` (text snippet) and `confidence_score` so users understand why they scored high or low.
- **Sentiment analysis** — Beyond presence/absence, the system classifies whether mentions are positive, neutral, or negative.
- **Periodic scheduling** — Users can set up weekly/biweekly/monthly auto-audits. A Celery Beat task (`dispatch_scheduled_audits`) runs every 15 minutes and checks for schedules whose `next_run_at` has passed.
- **Trend visualization** — The `/history/` endpoint returns all completed audit scores over time, powering a Chart.js line chart on the frontend.
- **Provider comparison** — The `/breakdown/` endpoint returns per-provider mention stats, powering a Chart.js bar chart showing GPT vs Claude vs Gemini vs Perplexity side-by-side.

## Celery Tasks

Runs on the `ai` queue (separate from default/integrations/webhooks) to avoid blocking other operations.

| Task | Purpose |
|---|---|
| `run_llm_ranking_audit` | Execute a complete audit with all prompts across all providers |
| `dispatch_scheduled_audits` | Celery Beat task (every 15 min) — creates audits for enabled schedules whose next_run_at has passed |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/<wid>/audits/` | List all audits for a website |
| POST | `/<wid>/audits/` | Create and queue a new audit |
| GET | `/<wid>/audits/<aid>/` | Get full audit with per-LLM results |
| DELETE | `/<wid>/audits/<aid>/` | Delete an audit |
| GET | `/<wid>/audits/<aid>/breakdown/` | Per-provider mention stats |
| GET | `/<wid>/audits/<aid>/recommendations/` | Actionable improvement suggestions |
| GET | `/<wid>/history/` | Historical scores for trend chart |
| GET | `/<wid>/schedule/` | Get current schedule |
| POST | `/<wid>/schedule/` | Create/update schedule |
| DELETE | `/<wid>/schedule/` | Remove schedule |

## Frontend Charts

- **Provider Comparison** — Bar chart (Chart.js via vue-chartjs) showing mention rate per LLM provider
- **Score Trend** — Line chart showing overall_score and mention_rate over time from completed audits

## Dependencies

- **Depends on:** `websites`, `accounts`, `core`
- **External:** Anthropic, OpenAI, Google AI, and Perplexity APIs
