# UI Design System (Airbnb-inspired, brand-tokenized)

The button / card / chip primitives in this folder are the canonical surface
elements for new pages. They reuse the existing brand CSS variables defined in
`frontend/src/assets/css/theme.css` — do NOT introduce new color tokens.

## Tokens used

- `--brand-accent`, `--brand-accent-hover`, `--brand-accent-glow`
- `--bg-card`, `--bg-card-hover`, `--bg-surface`
- `--border-color`, `--border-hover`
- `--text-primary`, `--text-secondary`, `--text-muted`
- `--color-success`, `--color-warning`, `--color-danger`, `--color-info`
  (each with a matching `*-bg` token)
- `--shadow-sm`, `--shadow-md`

## AirButton

Variants: `primary` | `secondary` | `ghost` | `outline` | `link` | `danger`
Sizes: `xs` | `sm` | `md` | `lg` | `xl`

- Pill-shape (`rounded-full`) by default; `outline` uses `rounded-xl` for a
  more grounded feel.
- `loading` swaps the left icon for a spinner and disables the button.
- `as="router-link"` + `to` for SPA links; `as="a"` + `href` for plain anchors.

```vue
<AirButton variant="primary" size="lg" @click="...">Run audit</AirButton>
<AirButton as="router-link" :to="`/llm-ranking/${id}`" variant="outline">Open</AirButton>
```

## AirCard

Sizes: `sm` (12px radius / sm shadow) | `md` (16px / sm) | `lg` (16px / sm) | `hero` (24px / md)

- `interactive` adds hover-lift + cursor-pointer.
- `as="router-link" | "button" | "a"` for clickable cards.
- Slots: default (body), `media` (banner — butted against the body),
  `header`, `footer`.
- Subcomponents: `AirCardHeader`, `AirCardTitle`, `AirCardSubtitle`,
  `AirCardFooter` — use these for typography consistency.

```vue
<AirCard size="md" interactive as="router-link" :to="...">
  <AirCardHeader>
    <AirCardTitle>...</AirCardTitle>
    <AirCardSubtitle>...</AirCardSubtitle>
  </AirCardHeader>
  ...
</AirCard>
```

## AirChip

Variants: `neutral` | `primary` | `success` | `warning` | `danger` | `info`
Sizes: `xs` | `sm` | `md`

- Always pill-shaped.
- `as="button"` to make it a focusable filter pill (used in
  ContentStudio, PromptLibrary, Accuracy).
- `closable` shows an X and emits `close`.

## Demo

Visit `/design-system` in dev (route is registered only when
`import.meta.env.DEV`).

## Hard rules

- No hard-coded hex colors. Always reference CSS variables.
- All interactive elements must have a visible `:focus-visible` ring.
- Don't reach for the Tailwind `bg-rose-*` / `text-pink-*` Airbnb palette —
  the project's accent is `--brand-accent` (not Airbnb pink).
