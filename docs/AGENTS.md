# Background Agents

What we can run autonomously, what each one reads, what it searches for, and when it is
allowed to speak.

## Principles

**1. A cron job does the same thing every time; an agent decides what is worth doing.**

This is the whole distinction, and today nothing crosses it. `dispatch_agent_runs` and
`dispatch_scheduled_audits` both ask only "whose `next_run_at` has passed?" The agents
themselves take a fixed gatherer's output and summarise it into a fixed JSON shape.
They observe and narrate; none of them choose. Adding a sixth narrator adds cost, not
value.

**2. Silent by default.**

An agent that speaks every day becomes wallpaper, and the one time it has something
urgent the user has already been trained to skip it. Every agent below has an explicit
"speaks when" condition, and for most of them the answer is "rarely". Silence is
simultaneously the better UX and the cheaper design.

**3. Reading your own data is nearly free; searching the world is not.**

The roster splits on this line deliberately. Tier 1 agents run statistics over data
already stored and cost close to nothing.

**4. Agent spend draws from the customer's allowance.**

Agents that decide to do more work compound in a way fixed schedules cannot. Tag
agent-initiated queries with a third `metadata["trigger"]` value (`agent`) alongside
`scheduled` and `adhoc`, so a customer sees what the agents spent on their behalf
separately from their own usage.

**5. Outward-facing actions stay human-gated.**

The existing allowlist (`ingest_url`, `draft_brief`, `notify`) is all internal and all
approval-gated, which is right. Auto-approve reversible internal actions; always ask
for anything that publishes, posts, or spends outside the platform.

## What exists today

`apps/agents/catalog.py` — five hired agents (Visibility Analyst, Citation Hunter,
Content Strategist, Lead Scout, Brand Watchdog). Declarative `AgentSpec` = persona
prompt + gatherer + allowed action types + optional entitlement key. Scheduled via
`dispatch_agent_runs`, spend-capped, human-gated.

`apps/brand_vault` security agents — Narrative Watch, LLM Truth, SERP Reputation,
Sentiment Pulse, Impersonation. Produce `SafetyAlert` rows with severity, grounded in
the tenant's own RAG chunks rather than asking a model cold.

The scaffolding is sound. What follows is what to do with it.

## Proposed roster

| # | Agent | Tier | Searches externally | Speaks |
|---|---|---|---|---|
| 1 | Cadence Planner | own data | no | monthly, or never |
| 2 | Movement Analyst | own data | no | only on real change |
| 3 | New Entrant Watch | own data | optional, to identify | on a new name crossing threshold |
| 4 | Source Gap Hunter | external | yes | weekly at most |
| 5 | Claim Auditor | external | no (internal diff) | only on factual mismatch |
| 6 | Impersonation Watch | external | yes | only on a hit |

Agents 5 and 6 already exist in `brand_vault` and need wiring, not building.

---

### 1. Cadence Planner — build this first

**Does:** Decides how often each tracked prompt should be measured, instead of
measuring all of them on one fixed cadence.

**Reads:** Per-prompt `LLMRankingResult` history, `mention_rate_smoothed`, the Wilson
confidence interval, rank variance over trailing weeks, whether the prompt has ever
produced a citation or an attributed visit.

**Searches:** Nothing. This is statistics over data already stored — most of it needs
no LLM call at all.

**Produces:** A per-prompt cadence assignment.

| Prompt state | Signal | Cadence |
|---|---|---|
| Stable — held #1 for weeks, tight CI | none | weekly |
| Volatile — bouncing #2 to #7 | high | daily or twice daily |
| Contested — new competitor just appeared | high | daily |
| Dead — no rank, no citations, no traffic | none | propose retirement |

**Speaks:** Monthly, summarising what it changed. Silent otherwise.

**Why first:** It is the only cost lever available that does not trade value for money.
Caching, batching and cheaper models all give something up. Reallocating cadence spends
the same allowance and buys *better* information, because the budget follows the
movement. It is also genuinely agentic — it decides — while costing almost nothing to
run.

**Implementation shape:** Cadence moves from `LLMRankingSchedule` (per-schedule) to a
field on `BrandPrompt` (per-prompt), and `dispatch_scheduled_audits` changes the
question it asks from "whose `next_run_at` passed?" to "what is worth measuring now?"

---

### 2. Movement Analyst

**Does:** Explains *why* a score moved. Today the number goes down and nobody says why.

**Reads:** The prompts whose rank or mention status changed, the stored
`LLMRankingResult.response_text` for both the before and after runs, the competitor set
on each, and the citation source classes behind them.

**Searches:** Nothing external. Everything it needs is already persisted — the raw
response text is stored verbatim, which is what makes the diff possible.

**Produces:** One paragraph:

> You dropped from #2 to #6 on "best CRM for startups" across Claude and Perplexity.
> Both answers now cite a G2 comparison page published March 3rd that ranks Competitor
> X above you. Your own G2 profile has not been updated since 2024.

**Speaks:** Only when a change clears a significance threshold — and the Wilson
interval is exactly the right test, so a two-query wobble never triggers it.

**Why it matters:** This is the "so what" layer. Competitors in this category are
consistently described as strong on measurement and weak on telling you what to do.
This is the cheapest possible way to be on the other side of that line, because it only
runs when something actually happened.

---

### 3. New Entrant Watch

**Does:** Notices brands appearing in your answer set that were not there before.

**Reads:** `competitors_mentioned` across recent results — it already carries name,
position, sentiment and domain per result.

**Searches:** Optionally one lookup to identify a genuinely unknown brand — what they
sell, and whether they are a real competitor or a false positive from extraction.

**Produces:**

> "Attio" appeared in 8 of your prompts this week, averaging rank 3. It has never
> appeared before.

**Speaks:** When a new name crosses a threshold — appears in N distinct prompts, or
above a rank floor. Not on a single stray mention.

**Why it matters:** Nearly free to derive from data already extracted, and nobody in
the category surfaces it. Competitive intelligence is a different buying trigger from
visibility monitoring, and it reaches a different budget.

---

### 4. Source Gap Hunter — the highest-leverage external agent

**Does:** Finds the specific sources that decide the prompts you lose, and tells you
which ones you are absent from.

**Reads:** Citations per prompt, source-class breakdown, and competitor share by source
class — all already computed by the citations app and rolled into
`SourceInfluenceSnapshot`.

**Searches:**

- The cited URLs themselves, to see what they say and whether you appear
- Review sites the answers lean on (G2, Capterra, TrustRadius) for your category
- Reddit and forum threads that rank for the query
- Documentation and comparison pages cited by the winning answers

**Produces:**

> Three sources decide "best analytics for SaaS": a G2 category page, a Reddit thread
> from r/SaaS, and Competitor X's own comparison page. You appear in none of them. The
> G2 page is cited most often.

**Speaks:** Weekly at most, and only when it finds a gap that is actually actionable.

**Why it matters:** This is the GEO-specific insight nobody else acts on. AI answers are
grounded in specific sources, so the highest-leverage action is not "write a blog post"
— it is "get into the three pages the models are actually reading." It also feeds
Content Studio a far better brief than gap-mining alone produces.

---

### 5. Claim Auditor (LLM Truth — exists, needs wiring)

**Does:** Detects AI assistants stating things about your product that are false.

**Reads:** Model answers about your brand, diffed against approved `BrandFact` rows in
the Brand Vault.

**Searches:** Nothing. It is a diff between what the models say and what you have
verified — which is precisely why it has a low false-positive rate, and why severity
judgements are grounded in tenant RAG chunks rather than asked cold.

**Produces:**

> ChatGPT is telling buyers you have no SOC 2. Your Brand Vault says certified
> 2026-03-11.

**Speaks:** Only on a factual mismatch — and this is the one alert class urgent enough
to justify an SMS. When a model states something false about you, it is being told to
every person who asks, invisibly, with the model's authority behind it. There is no
referrer, no impression log, nothing in analytics. The window to correct it matters.

**Pair it with reply-to-authorize:** the agent found the problem and can draft the
correction; the human approves from their phone with one word. That reduces the approval
gate to near-zero friction, which is what decides whether agentic features get used or
quietly abandoned.

---

### 6. Impersonation Watch (exists, needs wiring)

**Does:** Finds typosquat domains and fake social handles using your brand.

**Searches:** SERP for brand-adjacent domain permutations, social handles, and the
common typosquat patterns.

**Speaks:** Only on a hit. Also SMS-worthy.

---

## Sequencing

1. **Cadence Planner** — cuts cost while improving the product, needs no external
   search, and lands inside the existing dispatcher.
2. **Movement Analyst** — near-free, since it only runs on change, and it is the single
   biggest perceived-value jump: dashboard becomes analyst.
3. **Claim Auditor + Impersonation Watch** — already built; need delivery wiring and the
   alert-severity gate. Pair with SMS.
4. **Source Gap Hunter** — the most valuable and the most expensive. Build once
   allowance metering is in place so its spend is visible and bounded.
5. **New Entrant Watch** — cheap and opportunistic; ship whenever.

## Cost discipline

Agents 1, 2, 3 and 5 read data you already have and cost close to nothing. Only 4 and 6
do real external work. That split is deliberate: the roster should be mostly free to
run, so a customer never feels the agents competing with their own measurement budget.

Every agent-initiated query draws from the same allowance as scheduled and ad-hoc runs,
tagged `metadata["trigger"] = "agent"`. A per-tenant daily ceiling on agent-initiated
spend, separate from the user-initiated allowance, prevents a compounding loop — an
agent that decides to do more work is exactly the shape of bug that produces a surprise
bill.
