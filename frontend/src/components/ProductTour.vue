<template>
  <Teleport to="body">
    <div v-if="store.active && currentStep" class="tour-overlay" :class="{ ready: tooltipReady }">
      <div class="tour-tooltip" :style="tooltipStyle">
        <div class="tour-step-pill">Step {{ store.stepNumber }} of {{ store.totalSteps }}</div>
        <h4 class="tour-title">{{ currentStep.title }}</h4>
        <p class="tour-message">{{ currentStep.message }}</p>
        <div class="tour-actions">
          <button class="tour-skip" type="button" @click="onSkip">Skip tour</button>
          <div class="tour-actions-right">
            <button
              v-if="store.currentIndex > 0"
              class="tour-prev"
              type="button"
              @click="store.prev"
            >Back</button>
            <button class="tour-next" type="button" @click="onNext">
              {{ currentStep.cta || (store.isLastStep ? 'Done' : 'Next →') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
// ════════════════════════════════════════════════════════════════════
//  Renders the product-wide tour as a fixed tooltip over whichever
//  page the user happens to be on. Reads state from the tour pinia
//  store; navigates the router when the next step belongs to another
//  page; positions the tooltip relative to the step's target DOM node
//  once the page settles.
// ════════════════════════════════════════════════════════════════════

import { computed, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTourStore } from '@/stores/tour'

const store = useTourStore()
const router = useRouter()
const route = useRoute()

const tooltipPos = ref({ top: 0, left: 0 })
const tooltipReady = ref(false)
let highlightedEl = null

const currentStep = computed(() => store.currentStep)
const tooltipStyle = computed(() => ({
  top: tooltipPos.value.top + 'px',
  left: tooltipPos.value.left + 'px',
}))

function clearHighlight() {
  if (highlightedEl) {
    highlightedEl.classList.remove('tour-highlight')
    highlightedEl = null
  }
}

function applyHighlight(el) {
  clearHighlight()
  if (el) {
    el.classList.add('tour-highlight')
    highlightedEl = el
  }
}

function findTarget(selector) {
  if (!selector) return null
  // Targets allow comma-separated fallbacks so a step that prefers
  // `.lr-tabs` but should still anchor on `main` when tabs aren't in
  // the DOM (no audits yet, page still loading, etc.) works either
  // way. We pick the first selector that matches.
  for (const part of selector.split(',').map(s => s.trim())) {
    const el = document.querySelector(part)
    if (el) return el
  }
  return null
}

function positionTooltip() {
  const step = currentStep.value
  if (!step) return
  const el = findTarget(step.target)
  applyHighlight(el)

  const TOOLTIP_W = 340
  const TOOLTIP_H = 200
  const PAD = 14
  const vw = window.innerWidth
  const vh = window.innerHeight

  let top, left
  if (el) {
    const r = el.getBoundingClientRect()
    const pos = step.position || 'bottom'
    if (pos === 'bottom') {
      top = r.bottom + PAD
      left = r.left + r.width / 2 - TOOLTIP_W / 2
    } else if (pos === 'top') {
      top = r.top - TOOLTIP_H - PAD
      left = r.left + r.width / 2 - TOOLTIP_W / 2
    } else if (pos === 'left') {
      top = r.top + r.height / 2 - TOOLTIP_H / 2
      left = r.left - TOOLTIP_W - PAD
    } else if (pos === 'right') {
      top = r.top + r.height / 2 - TOOLTIP_H / 2
      left = r.right + PAD
    }
  } else {
    // No target — center it. Happens on empty pages or routes we
    // haven't fully decorated yet; the tour still progresses.
    top = vh / 2 - TOOLTIP_H / 2
    left = vw / 2 - TOOLTIP_W / 2
  }

  top = Math.max(12, Math.min(vh - TOOLTIP_H - 12, top))
  left = Math.max(12, Math.min(vw - TOOLTIP_W - 12, left))
  tooltipPos.value = { top, left }
  tooltipReady.value = true
}

async function syncRouteAndPosition() {
  const step = currentStep.value
  if (!step) return

  tooltipReady.value = false

  // Navigate if the step belongs to a different route.
  const targetName = step.route?.name
  if (targetName && route.name !== targetName) {
    try {
      await router.push(step.route)
    } catch (_) {
      // Navigation failure (guard redirect, etc.) — keep tour alive
      // and just try to position on whatever page we landed on.
    }
  }

  // Wait for the new page to mount its target DOM. Two ticks is
  // enough for the lazy-loaded route component + its child cards.
  await nextTick()
  setTimeout(positionTooltip, 120)
}

function onNext() {
  clearHighlight()
  store.next()
}

function onSkip() {
  clearHighlight()
  store.skip()
}

// React to step changes, including the first activation.
watch(
  () => [store.active, store.currentIndex],
  ([isActive]) => {
    if (!isActive) {
      clearHighlight()
      tooltipReady.value = false
      return
    }
    syncRouteAndPosition()
  },
  { immediate: true },
)

// If the page resizes or scrolls, keep the tooltip pinned.
const onResize = () => positionTooltip()
const onScroll = () => positionTooltip()
window.addEventListener('resize', onResize)
window.addEventListener('scroll', onScroll, true)
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onScroll, true)
  clearHighlight()
})
</script>

<style>
/* Global — highlight ring lives on whichever element the current step
   targets. Kept at low specificity so page styles don't override. */
.tour-highlight {
  position: relative;
  z-index: 1001;
  box-shadow:
    0 0 0 4px rgba(255, 107, 53, 0.40),
    0 0 30px rgba(255, 107, 53, 0.15) !important;
  border-radius: 10px;
  transition: box-shadow 0.2s ease;
  animation: tour-pulse 2.4s ease-in-out infinite;
}
@keyframes tour-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.40), 0 0 30px rgba(255, 107, 53, 0.15); }
  50%      { box-shadow: 0 0 0 8px rgba(255, 107, 53, 0.20), 0 0 40px rgba(255, 107, 53, 0.10); }
}
</style>

<style scoped>
.tour-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.18s ease;
}
.tour-overlay.ready { opacity: 1; }

.tour-tooltip {
  position: fixed;
  width: 340px;
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 14px;
  padding: 20px 22px 18px;
  box-shadow: 0 20px 50px -16px rgba(20, 23, 24, 0.18), 0 0 0 1px rgba(20,23,24,0.04);
  pointer-events: auto;
}

.tour-step-pill {
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--brand-accent, #ff6b35);
  background: rgba(255, 107, 53, 0.10);
  padding: 3px 9px;
  border-radius: 999px;
  margin-bottom: 10px;
}

.tour-title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary, #131718);
  letter-spacing: -0.01em;
}

.tour-message {
  margin: 0 0 18px;
  font-size: 0.85rem;
  line-height: 1.55;
  color: var(--text-secondary, #4b5563);
}

.tour-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tour-actions-right { display: flex; gap: 6px; }

.tour-skip {
  appearance: none;
  background: transparent;
  border: none;
  font-size: 0.78rem;
  color: var(--text-muted, #6b7280);
  cursor: pointer;
  padding: 6px 4px;
}
.tour-skip:hover { color: var(--text-primary); }

.tour-prev {
  appearance: none;
  background: var(--bg-subtle, #fafafa);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  font-size: 0.82rem;
  color: var(--text-primary, #131718);
  padding: 7px 14px;
  cursor: pointer;
  font-weight: 500;
}
.tour-prev:hover { background: var(--border-color, #e5e7eb); }

.tour-next {
  appearance: none;
  background: var(--text-primary, #131718);
  color: var(--text-inverse, #ffffff);
  border: none;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 8px 16px;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.tour-next:hover { opacity: 0.88; }
</style>
