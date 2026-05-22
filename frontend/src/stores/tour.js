import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'

// ════════════════════════════════════════════════════════════════════
//  Product tour — a cross-page guided walkthrough.
//
//  Differs from the per-page OnboardingTooltip in components/: this
//  store drives a single tour that navigates the user from page to
//  page (Dashboard → LLM Dashboard → Prompt Library → … → Content
//  Studio) and is mounted globally in AppLayout via ProductTour.vue.
//
//  Each step declares the route it belongs to. When advancing to a
//  step whose route differs from the current location, the tour
//  component pushes that route first and waits for the next page to
//  mount before showing the tooltip.
//
//  Completion is tracked per-user in localStorage so logging in as
//  someone else doesn't suppress their first-run tour.
// ════════════════════════════════════════════════════════════════════

const TOUR_STORAGE_PREFIX = 'fb_product_tour_done_'

export const useTourStore = defineStore('tour', () => {
  const active = ref(false)
  const currentIndex = ref(0)
  // The websiteId is injected at start(); without it, the cross-page
  // routes that include :websiteId can't be built. If no website is
  // selected yet (fresh signup), the tour starts on /dashboard only
  // and prompts the user to create or pick a project.
  const websiteId = ref(null)

  function buildSteps(wid) {
    // A wid-less tour stops after the dashboard step; the others
    // require a selected project to navigate to.
    const projectSteps = wid
      ? [
          {
            route: { name: 'llm-ranking', params: { websiteId: wid } },
            target: '.lr-tabs',
            title: 'Your LLM Dashboard',
            message:
              "This is where you'll see how AI models talk about your brand. It's empty right now because no audits have run. Audits need prompts — let's set those up first.",
            position: 'bottom',
            cta: 'Show me prompts →',
          },
          {
            route: { name: 'prompt-library', params: { websiteId: wid } },
            target: '.page-header, .page-title, main',
            title: 'Prompt Library',
            message:
              "Prompts are the questions we'll send to Claude, GPT-4, Gemini, and Perplexity. Browse the repository for templates that match your industry, or write your own.",
            position: 'bottom',
          },
          {
            route: { name: 'llm-ranking', params: { websiteId: wid } },
            target: '.header-actions, .btn-primary',
            title: 'Run an audit',
            message:
              "With prompts in place, click Run New Audit to send them to every configured model. Each query is logged and the results land on the Overview and Performance tabs.",
            position: 'left',
          },
          {
            route: { name: 'llm-ranking', params: { websiteId: wid } },
            target: '.lr-tab:nth-of-type(3), [aria-selected]',
            title: 'Pages tab',
            message:
              "Before running an audit, attach pages from your site so the models have your latest copy. Drag & drop docs or paste URLs — agents read each one as context.",
            position: 'bottom',
          },
          {
            route: { name: 'llm-ranking', params: { websiteId: wid } },
            target: '.lr-tab:nth-of-type(2)',
            title: 'Performance tab',
            message:
              "Once an audit completes, jump here for per-model charts: mention rate by model, prompt × model heatmap, and your visibility trend over time.",
            position: 'bottom',
          },
          {
            route: { name: 'source-influence', params: { websiteId: wid } },
            target: '.page-header, .page-title, main',
            title: 'Source Influence',
            message:
              "Which websites do the models cite when they answer your prompts? This page surfaces the third-party sources that shape AI answers about your industry.",
            position: 'bottom',
          },
          {
            route: { name: 'brand-vault', params: { websiteId: wid } },
            target: '.page-header, .page-title, main',
            title: 'Brand Vault',
            message:
              "The single source of truth about your brand. Facts curated here are used by our agents as grounding for content generation and audit scoring.",
            position: 'bottom',
          },
          {
            route: { name: 'content-studio', params: { websiteId: wid } },
            target: '.page-header, .page-title, main',
            title: 'Content Studio',
            message:
              "When you're missing from a prompt, this is where you close the gap. Studio generates briefs and drafts grounded in your Brand Vault, ready to publish.",
            position: 'bottom',
            cta: 'Finish tour',
          },
        ]
      : []

    return [
      {
        route: { name: 'dashboard' },
        target: '.project-card, .project-grid, main, body',
        title: 'Welcome — start here',
        message:
          wid
            ? "Every project on this page tracks one website. Open one and we'll walk through the AI visibility flow together."
            : "Every project tracks one website. Create or pick a project first — then re-run the tour to walk through the AI visibility flow.",
        position: 'bottom',
        cta: wid ? "Let's go →" : 'Got it',
      },
      ...projectSteps,
    ]
  }

  const steps = ref([])
  const currentStep = computed(() => steps.value[currentIndex.value] || null)
  const totalSteps = computed(() => steps.value.length)
  const stepNumber = computed(() => currentIndex.value + 1)
  const isLastStep = computed(() => currentIndex.value >= steps.value.length - 1)

  function storageKey() {
    const auth = useAuthStore()
    const uid = auth.user?.id || 'anon'
    return TOUR_STORAGE_PREFIX + uid
  }

  function isDone() {
    try {
      return localStorage.getItem(storageKey()) === 'true'
    } catch (_) {
      return false
    }
  }

  function start(wid) {
    websiteId.value = wid || null
    steps.value = buildSteps(websiteId.value)
    currentIndex.value = 0
    active.value = true
  }

  function next() {
    if (currentIndex.value >= steps.value.length - 1) {
      finish()
      return
    }
    currentIndex.value++
  }

  function prev() {
    if (currentIndex.value > 0) currentIndex.value--
  }

  function skip() {
    finish()
  }

  function finish() {
    active.value = false
    try {
      localStorage.setItem(storageKey(), 'true')
    } catch (_) {
      // Storage may be disabled (private mode etc.) — tour just won't
      // remember completion. Harmless.
    }
  }

  // Manually surfaced helper so the AppLayout's "Take a tour" button
  // can re-trigger even after the user already completed it once.
  function reset(wid) {
    try {
      localStorage.removeItem(storageKey())
    } catch (_) {}
    start(wid)
  }

  return {
    active,
    currentIndex,
    websiteId,
    steps,
    currentStep,
    totalSteps,
    stepNumber,
    isLastStep,
    isDone,
    start,
    next,
    prev,
    skip,
    finish,
    reset,
  }
})
