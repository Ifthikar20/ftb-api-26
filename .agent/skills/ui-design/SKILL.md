---
description: UI design rules and conventions for all FetchBot frontend changes. Apply to every frontend modification.
---

# FetchBot UI Design Rules

These rules MUST be applied to every frontend/UI change across the FetchBot platform.

## No Emojis

- **Never use emojis** in any production UI component, template, or data object
- Use **SVG icons** or **CSS-styled indicators** (colored dots, badges, border accents) instead
- Emojis are acceptable ONLY in: commit messages, console logs, and developer-facing comments
- When replacing emojis in data objects, rename `emoji` properties to `icon` and use HTML icon strings rendered via `v-html`

## SVG Icon Patterns

For inline icons in buttons/badges:
```html
<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">...</svg>
```

For status indicators, use colored dots:
```html
<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--color-success)"></span>
```

Status colors:
- Success/positive: `var(--color-success)` or `#22c55e`
- Warning/caution: `var(--color-warning)` or `#f59e0b`
- Danger/negative: `var(--color-danger)` or `#ef4444`
- Neutral/muted: `var(--text-muted)` or `#94a3b8`
- Info/accent: `var(--brand-accent)` or `#5B8DEF`

## Typography

- Use design system fonts via CSS variables: `var(--font-family)` for body, `var(--font-display)` for headings
- Body font: `Plus Jakarta Sans` (via `--font-family`)
- Display font: `DM Serif Display` (via `--font-display`)
- Code font: `SF Mono` (for code blocks only)
- Never use browser default fonts

## Color Palette

- Always use CSS custom properties: `--brand-accent`, `--text-primary`, `--bg-card`, etc.
- Never use raw hex colors for UI text or backgrounds
- Exception: SVG inline styles may use hex values matching design system colors

## Data Presentation

- Show **real data only** -- never seed or hardcode dummy/fake data
- All values must come from API responses or computed from real data
- If no data exists, show a clear **empty state** with instructions and an SVG icon (no emoji)

## Component Patterns

- Buttons: Use `.btn .btn-primary`, `.btn .btn-secondary`, `.btn .btn-sm` classes
- Badges: Use `.badge .badge-success`, `.badge-warning`, `.badge-danger`, `.badge-neutral`, `.badge-info`, `.badge-accent`
- Cards: Use `.card` with optional `.card-header` and `.card-title`
- Tables: Use `.data-table` with proper `thead`/`tbody`
- Modals: Use `.modal-overlay` > `.modal-content` > `.modal-header` pattern
