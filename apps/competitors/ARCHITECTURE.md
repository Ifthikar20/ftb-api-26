# Competitors App

## Purpose

Tracks competitor websites, detects changes (new pages, ranking shifts, content updates, pricing changes), and identifies keyword gaps. Provides the data layer for the `competitor_watcher` agent and the competitive analysis dashboard.

## Architecture

```
Weekly Celery Beat
  │
  ▼
crawl_all_competitors (Monday 1 AM)
  │
  ├── For each Competitor:
  │     ├── Crawl competitor_url
  │     ├── ChangeDetectionService.detect_changes()
  │     │     ├── Compare against previous CompetitorSnapshot
  │     │     └── Create CompetitorChange records
  │     ├── Create new CompetitorSnapshot
  │     └── ComparisonService.find_keyword_gaps()
  │           └── Create/update KeywordGap records
  │
  └── Agents / Dashboard read from stored data
```

## Models

| Model | Purpose |
|---|---|
| `Competitor` | A tracked competitor website. Stores URL, name, auto-detected flag, estimated traffic, domain authority, and threat level (low/medium/high/critical). |
| `CompetitorSnapshot` | Point-in-time metrics capture: traffic estimate, keyword count, backlink count, content count, and a flexible `metrics` JSON field. |
| `KeywordGap` | Keyword gap analysis. Shows keywords where competitors rank but your site doesn't (or ranks lower). Includes search volume, difficulty, and opportunity score. |
| `CompetitorChange` | Detected changes: new_page, removed_page, ranking_change, content_update, pricing_change. Stored with JSON detail. |

## Services

| Service | Purpose |
|---|---|
| `ChangeDetectionService` | Compares current crawl against previous snapshot to detect changes |
| `ComparisonService` | Finds keyword gaps between user's site and competitors |

## Celery Tasks

| Task | Schedule | Purpose |
|---|---|---|
| `crawl_all_competitors` | Weekly (Monday 1 AM) | Crawl all tracked competitors, detect changes, update snapshots |

## Key Design Decisions

- **Threat levels** — Competitors are assigned a threat level (low/medium/high/critical) based on traffic overlap and ranking proximity.
- **Auto-detection** — Competitors can be auto-detected from SERP overlap or manually added by the user.
- **Snapshot-based change detection** — Each crawl creates a snapshot; changes are derived by diffing consecutive snapshots.
- **Keyword gap scoring** — `opportunity_score` weights volume, difficulty, and rank gap to prioritize actionable keywords.

## Dependencies

- **Depends on:** `websites`, `core`
- **Depended on by:** `agents` (competitor_watcher agent type uses this data)
