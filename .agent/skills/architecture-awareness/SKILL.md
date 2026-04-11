---
description: Read and update ARCHITECTURE.md + .todo.md before and after modifying any Django app. Apply when creating, modifying, or deleting models, services, tasks, views, or any structural code in apps/.
---

# Architecture & TODO Awareness

Every Django app in `apps/` has two mandatory documentation files:

- **`ARCHITECTURE.md`** — How the app works: models, services, tasks, design decisions, dependencies.
- **`.todo.md`** — What's pending, in-progress, and done.

Both files are the source of truth. You **must** read both before and update both after any change.

## Before Making Changes

**Always read BOTH files before touching an app.**

1. Identify which app(s) your change affects.
2. Read `apps/<app_name>/ARCHITECTURE.md` for each affected app.
3. Read `apps/<app_name>/.todo.md` to understand what's pending and what's already done.
4. Check the **Dependencies** section in ARCHITECTURE.md to understand what other apps are affected.

```
# Example: before modifying the leads app
Read: apps/leads/ARCHITECTURE.md
Read: apps/leads/.todo.md
Check: Dependencies section — leads depends on analytics, websites, accounts, core
Check: Depended on by — voice_agent, agents, social_leads use leads
Check: .todo.md — is this work already tracked? Is it in progress?
```

If either file is missing for an app, create it following the formats below before starting work.

## After Making Changes

**Always update BOTH files after completing your changes.**

### ARCHITECTURE.md — update when:

| Change Type | Sections to Update |
|---|---|
| Add/modify/remove a model | **Models** table |
| Add/modify/remove a service | **Services** table |
| Add/modify/remove a Celery task | **Celery Tasks** table |
| Add a new external dependency | **Dependencies** section |
| Change the data flow or architecture | **Architecture** diagram |
| Add a new design pattern or convention | **Key Design Decisions** section |

### .todo.md — update when:

| Change Type | What to Update |
|---|---|
| Starting work on a tracked item | Move from **Open** to **In Progress** |
| Completing a tracked item | Move from **In Progress** to **Done**, mark `[x]` |
| Discovering new work needed | Add to **Open** section |
| Completing untracked work | Add directly to **Done** section |
| Abandoning an item | Remove or add a note explaining why |

Keep updates concise. Match the existing style.

## .todo.md Format

```markdown
# <App Name> — TODO

## Open

- `[ ]` Description of pending work
- `[ ]` Another pending item

## In Progress

- `[/]` Item currently being worked on

## Done

- `[x]` Completed item with brief description
```

## ARCHITECTURE.md Format

```markdown
# <App Name> App

## Purpose
One paragraph explaining what this app does and why it exists.

## Architecture
ASCII diagram showing the data flow and key components.

## Models
Table with columns: Model | Purpose

## Services
Table with columns: Service | Purpose

## Celery Tasks
Table with columns: Task | Schedule | Purpose

## Key Design Decisions
Bullet list of important architectural choices and their rationale.

## Dependencies
- **Depends on:** list of apps this app imports from
- **Depended on by:** list of apps that import from this app
- **External:** third-party APIs or services used
```

## App Index

| App | Architecture | TODO |
|---|---|---|
| `accounts` | `apps/accounts/ARCHITECTURE.md` | `apps/accounts/.todo.md` |
| `agents` | `apps/agents/ARCHITECTURE.md` | `apps/agents/.todo.md` |
| `analytics` | `apps/analytics/ARCHITECTURE.md` | `apps/analytics/.todo.md` |
| `billing` | `apps/billing/ARCHITECTURE.md` | `apps/billing/.todo.md` |
| `competitors` | `apps/competitors/ARCHITECTURE.md` | `apps/competitors/.todo.md` |
| `compliance` | `apps/compliance/ARCHITECTURE.md` | `apps/compliance/.todo.md` |
| `leads` | `apps/leads/ARCHITECTURE.md` | `apps/leads/.todo.md` |
| `llm_ranking` | `apps/llm_ranking/ARCHITECTURE.md` | `apps/llm_ranking/.todo.md` |
| `notifications` | `apps/notifications/ARCHITECTURE.md` | `apps/notifications/.todo.md` |
| `social_leads` | `apps/social_leads/ARCHITECTURE.md` | `apps/social_leads/.todo.md` |
| `voice_agent` | `apps/voice_agent/ARCHITECTURE.md` | `apps/voice_agent/.todo.md` |
| `websites` | `apps/websites/ARCHITECTURE.md` | `apps/websites/.todo.md` |

## Cross-App Changes

When a change spans multiple apps:

1. Read ALL affected ARCHITECTURE.md **and** .todo.md files first.
2. Check dependency directions to avoid circular imports.
3. After completing the change, update ALL affected ARCHITECTURE.md **and** .todo.md files.
4. If you add a new dependency between apps, update both the "Depends on" and "Depended on by" sections in both apps.

## Enforcement

- Never skip the read step. Even for "simple" changes, the ARCHITECTURE.md may reveal constraints and the .todo.md may show the item is already tracked or done.
- Never skip the update step. Stale documentation is worse than no documentation.
- If you find either file is inaccurate, fix it as part of your change.
- New apps must have both `ARCHITECTURE.md` and `.todo.md` created before any code is written.
