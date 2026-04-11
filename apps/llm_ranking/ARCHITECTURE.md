# LLM Ranking App

## Purpose

Measures how prominently a business appears in AI-generated answers across major LLMs (Claude, GPT-4, Gemini, Perplexity). This is "SEO for AI" — understanding and improving your visibility when people ask AI assistants about your industry.

## Architecture

```
User triggers audit
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

## Celery Tasks

Runs on the `ai` queue (separate from default/integrations/webhooks) to avoid blocking other operations.

| Task | Purpose |
|---|---|
| `run_llm_ranking_audit` | Execute a complete audit with all prompts across all providers |

## Dependencies

- **Depends on:** `websites`, `accounts`, `core`
- **External:** Anthropic, OpenAI, Google AI, and Perplexity APIs
