# Content Studio — Design Tokens

Airbnb-inspired visual language. New components and pages under
`/llm-ranking/:websiteId/content` should follow these tokens so the
surface stays warm, calm, and consistent.

## Spacing scale

| Token         | px     | Use                                                |
|---------------|--------|----------------------------------------------------|
| `cs-space-1`  | 4      | Inline icon gap                                    |
| `cs-space-2`  | 8      | Tight badge / chip padding                         |
| `cs-space-3`  | 12     | Card inner gap                                     |
| `cs-space-4`  | 16     | Card body padding (small)                          |
| `cs-space-6`  | 24     | Default card padding (`p-6`)                       |
| `cs-space-8`  | 32     | Generous card padding for hero / stat strip        |
| `cs-space-12` | 48     | Section spacing (between hero and stats etc.)      |
| `cs-space-16` | 64     | Page top/bottom breathing room                     |

Translate directly into Tailwind utilities — `p-6`, `p-8`, `gap-6`,
`mb-12`, `py-16`.

## Radius

- Cards: `rounded-2xl` (16px) for resting cards, `rounded-3xl` (24px) for hero / large surfaces.
- Pills & chips: `rounded-full`.
- Primary CTA buttons: `rounded-full`.
- Inputs: `rounded-xl` (12px).

## Color tokens

Warm neutrals + a single accent.

| Token                 | Light hex   | Use                                             |
|-----------------------|-------------|-------------------------------------------------|
| `--cs-text-primary`   | `#0f172a`   | Headlines, primary body                         |
| `--cs-text-secondary` | `#64748b`   | Secondary copy, helper text                     |
| `--cs-text-muted`     | `#94a3b8`   | Captions, disabled                              |
| `--cs-bg-page`        | `#fafaf9`   | Page background (warm zinc-50)                  |
| `--cs-bg-card`        | `#ffffff`   | Card surface                                    |
| `--cs-bg-subtle`      | `#f4f4f5`   | Subtle wash for empty states / quiet sections   |
| `--cs-border`         | `#e4e4e7`   | Hairline border                                 |
| `--brand-rose`        | `#FF385C`   | Primary CTA, single accent                      |
| `--brand-rose-hover`  | `#E11D48`   | CTA hover                                       |

Gap-type accents (used inside `GapTypeBadge`):

| Gap type    | Background       | Foreground      |
|-------------|------------------|-----------------|
| visibility  | `bg-blue-50`     | `text-blue-700` |
| accuracy    | `bg-amber-50`    | `text-amber-700`|
| citation    | `bg-emerald-50`  | `text-emerald-700` |
| generic     | `bg-zinc-100`    | `text-zinc-700` |

Quality score bar:

- `< 0.5` -> `bg-amber-500`
- `0.5 - 0.8` -> `bg-blue-500`
- `> 0.8` -> `bg-emerald-500`

## Shadows

- Resting card: `shadow-sm` (`0 1px 2px rgba(15,23,42,0.04)`).
- Hover card: `shadow-md` plus `-translate-y-0.5` (1-2px lift).
- Modal: `shadow-lg`.

Never use harsh / colored shadows.

## Typography

- System / Inter stack inherited from app theme.
- Body: 14-15px (`text-sm` / `text-[15px]`), line-height 1.5-1.6.
- Card headline: `text-[15px] font-medium`.
- Page title: `text-3xl font-semibold tracking-tight` (32px).
- Page subtitle: `text-base text-zinc-500`.

## Motion

- Hover lift: `transition-all duration-150 ease-out` plus
  `hover:-translate-y-0.5 hover:shadow-md`.
- Modal / drawer enter: 200ms `cubic-bezier(0.23, 1, 0.32, 1)`.
- Page transitions inherit the existing `page-fade` from AppLayout.

## Buttons

- Primary CTA: `.btn-rose` — rose-500 fill, white text, rounded-full.
- Secondary: `.btn-rose-outline` — rose border, rose text, rounded-full.
- Tertiary / quiet: zinc-100 background, zinc-900 text, rounded-full.

Use rose **sparingly**: at most one per visible card cluster.

## Empty states

Always render an empty state with: a soft icon (zinc-300/400, 48px),
a one-line warm heading (zinc-900), a one-line helper (zinc-500), and
where actionable, a single rose CTA. No empty grids.
