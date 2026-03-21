---
description: UI design rules and conventions for all FetchBot frontend changes
---

# UI Design Rules

These rules MUST be followed for every frontend/UI change.

## No Emojis in UI
- **Never use emojis** (🔥, 📊, ⚠️, etc.) in the production UI
- Use **SVG icons** or **CSS-styled indicators** instead
- Emojis are acceptable ONLY in: commit messages, console logs, and developer-facing comments

## Visual Indicators
- Use colored dots, badges, or border accents instead of emojis
- Status indicators: green for success, amber for warning, red for danger
- Use icon SVGs from the existing icon system

## Data Presentation
- Show **real data only** — never seed or hardcode dummy/fake data
- All values must come from API responses or computed from real data
- If no data exists, show a clear empty state with instructions

## Typography
- Use the design system fonts (Inter, SF Mono for code)
- Never use browser default fonts

## Color Palette
- Use design system CSS variables (--brand-accent, --text-primary, etc.)
- Never use raw hex colors for UI text or backgrounds
