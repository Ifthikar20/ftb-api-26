---
description: Vue.js frontend development patterns for FetchBot. Apply when creating or modifying frontend pages, components, or stores.
---

# FetchBot Frontend Patterns

Follow these conventions when working on the FetchBot Vue.js frontend.

## Tech Stack

- **Framework**: Vue 3 with Composition API (`<script setup>`)
- **State**: Pinia stores (`src/stores/`)
- **Routing**: Vue Router 4 (`src/router/index.js`)
- **HTTP**: Axios via centralized client (`src/api/client.js`)
- **Charts**: Chart.js + vue-chartjs
- **Flow diagrams**: @vue-flow/core (pipeline views)
- **Build**: Vite 7

## File Structure

```
frontend/src/
  main.js                 # App entry point
  App.vue                 # Root component
  router/index.js         # Routes with auth guards
  stores/
    auth.js               # Auth state + JWT refresh
    app.js                # App-wide state (active website, theme)
  api/
    client.js             # Axios instance with interceptors
    <feature>.js           # API module per feature
  pages/
    LandingPage.vue       # Public landing page
    auth/                 # Login, Register, ForgotPassword, VerifyEmail
    DashboardPage.vue
    LeadsPage.vue
    AnalyticsPage.vue
    ...
  components/
    PipelineNode.vue      # VueFlow custom node
    ...
  layouts/
    AppLayout.vue         # Authenticated layout with sidebar
  assets/
    main.css              # Design system (CSS variables, components)
```

## Page Structure

All authenticated pages are wrapped in `AppLayout.vue` via the `protect()` helper in the router.

```javascript
// Router pattern
const protect = (path, name, component, props = false) => ({
    path,
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [{ path: '', name, component, props }]
})
```

## API Modules

Each feature has a dedicated API module in `src/api/`:

```javascript
import api from './client'

export default {
    list: (wid, params) => api.get(`/leads/${wid}/`, { params }),
    get: (wid, lid) => api.get(`/leads/${wid}/${lid}/`),
    update: (wid, lid, data) => api.put(`/leads/${wid}/${lid}/`, data),
}
```

## Component Conventions

- Use `<script setup>` (Composition API) for all components
- Use `ref()` and `computed()` for reactive state
- Use `onMounted()` for data fetching
- Destructure route params: `const route = useRoute(); const id = route.params.websiteId`

## Animation System

- Use `.anim` class with `data-anim="fade-up"` for scroll-triggered reveals
- Register IntersectionObserver in `onMounted()`
- Add `.in` class when element enters viewport
- Use `data-delay` for staggered animations

```javascript
onMounted(() => {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const d = parseInt(e.target.dataset.delay || '0')
        setTimeout(() => e.target.classList.add('in'), d)
        obs.unobserve(e.target)
      }
    })
  }, { threshold: 0.1 })
  document.querySelectorAll('.anim').forEach(el => obs.observe(el))
})
```

## Design System (CSS Variables)

All styling uses CSS custom properties from `main.css`:

| Category | Variables |
|----------|-----------|
| Background | `--bg-root`, `--bg-card`, `--bg-surface`, `--bg-input` |
| Text | `--text-primary`, `--text-secondary`, `--text-muted` |
| Brand | `--brand-accent`, `--brand-primary` |
| Status | `--color-success`, `--color-warning`, `--color-danger`, `--color-info` |
| Borders | `--border-color`, `--border-hover` |
| Shadows | `--shadow-sm`, `--shadow-md`, `--shadow-lg` |
| Radius | `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-full` |
| Fonts | `--font-family`, `--font-display` |
| Sizes | `--font-xs` through `--font-4xl` |

Supports dark mode via `[data-theme="dark"]` selector.

## Critical Rules

1. **No emojis** in any UI component, template, or data -- use SVG icons or colored indicators
2. **No raw hex colors** -- use CSS variables
3. **No dummy data** -- real API data or empty states only
4. **Responsive** -- always handle mobile via `@media (max-width: 900px)` and `@media (max-width: 640px)`
