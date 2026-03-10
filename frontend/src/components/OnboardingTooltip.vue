<template>
  <Teleport to="body">
    <div v-if="visible" class="onboarding-overlay">
      <div class="tooltip-card" :style="tooltipStyle">
        <div class="tooltip-arrow" :class="arrowClass"></div>
        <div class="tooltip-step">Step {{ step }} of {{ totalSteps }}</div>
        <h4 class="tooltip-title">{{ title }}</h4>
        <p class="tooltip-body">{{ message }}</p>
        <div class="tooltip-actions">
          <button class="tooltip-skip" @click="skip">Skip all</button>
          <button class="tooltip-next" @click="next">
            {{ step === totalSteps ? 'Got it!' : 'Next →' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  steps: { type: Array, required: true },  // [{target, title, message, position}]
  storageKey: { type: String, default: 'fb_onboarding_done' },
})

const emit = defineEmits(['complete'])

const step = ref(1)
const visible = ref(false)
const tooltipPos = ref({ top: 0, left: 0 })

const totalSteps = computed(() => props.steps.length)
const currentStep = computed(() => props.steps[step.value - 1] || {})
const title = computed(() => currentStep.value.title || '')
const message = computed(() => currentStep.value.message || '')
const arrowClass = computed(() => `arrow-${currentStep.value.position || 'bottom'}`)

const tooltipStyle = computed(() => ({
  top: tooltipPos.value.top + 'px',
  left: tooltipPos.value.left + 'px',
}))

function positionTooltip() {
  const s = currentStep.value
  if (!s.target) return
  const el = document.querySelector(s.target)
  if (!el) return

  const rect = el.getBoundingClientRect()
  const pos = s.position || 'bottom'
  let top = 0, left = 0

  if (pos === 'bottom') {
    top = rect.bottom + 12
    left = rect.left + rect.width / 2 - 160
  } else if (pos === 'top') {
    top = rect.top - 200
    left = rect.left + rect.width / 2 - 160
  } else if (pos === 'right') {
    top = rect.top + rect.height / 2 - 60
    left = rect.right + 12
  } else if (pos === 'left') {
    top = rect.top + rect.height / 2 - 60
    left = rect.left - 340
  }

  // Clamp to viewport
  top = Math.max(10, Math.min(window.innerHeight - 220, top))
  left = Math.max(10, Math.min(window.innerWidth - 340, left))
  tooltipPos.value = { top, left }

  // Add highlight ring to target
  el.classList.add('onboarding-highlight')
}

function clearHighlights() {
  document.querySelectorAll('.onboarding-highlight').forEach(el => {
    el.classList.remove('onboarding-highlight')
  })
}

function next() {
  clearHighlights()
  if (step.value >= totalSteps.value) {
    finish()
    return
  }
  step.value++
  setTimeout(positionTooltip, 50)
}

function skip() {
  clearHighlights()
  finish()
}

function finish() {
  visible.value = false
  localStorage.setItem(props.storageKey, 'true')
  emit('complete')
}

onMounted(() => {
  if (localStorage.getItem(props.storageKey) === 'true') return
  // Delay to let page render
  setTimeout(() => {
    visible.value = true
    positionTooltip()
  }, 800)
})

onUnmounted(clearHighlights)

watch(step, () => { setTimeout(positionTooltip, 50) })
</script>

<style>
/* Global — the highlight ring applied to target elements */
.onboarding-highlight {
  position: relative;
  z-index: 1001;
  box-shadow: 0 0 0 4px rgba(201, 160, 80, 0.4), 0 0 20px rgba(201, 160, 80, 0.15) !important;
  border-radius: 8px;
  animation: onboarding-pulse 2s infinite;
}

@keyframes onboarding-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(201, 160, 80, 0.4), 0 0 20px rgba(201, 160, 80, 0.15); }
  50% { box-shadow: 0 0 0 8px rgba(201, 160, 80, 0.2), 0 0 30px rgba(201, 160, 80, 0.1); }
}
</style>

<style scoped>
.onboarding-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  pointer-events: none;
}

.tooltip-card {
  position: fixed;
  width: 320px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-lg), 0 0 60px rgba(0,0,0,0.1);
  pointer-events: all;
  z-index: 1002;
}

.tooltip-step {
  font-size: 11px;
  font-weight: 700;
  color: var(--brand-accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.tooltip-title {
  font-size: var(--font-md);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.tooltip-body {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 16px;
}

.tooltip-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tooltip-skip {
  background: none;
  border: none;
  font-size: var(--font-xs);
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
}

.tooltip-skip:hover { color: var(--text-primary); }

.tooltip-next {
  background: var(--text-primary);
  color: var(--text-inverse);
  border: none;
  padding: 8px 20px;
  border-radius: var(--radius-full);
  font-size: var(--font-sm);
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.tooltip-next:hover { opacity: 0.85; }

.tooltip-arrow {
  position: absolute;
  width: 12px;
  height: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transform: rotate(45deg);
}

.arrow-bottom .tooltip-arrow,
.arrow-bottom.tooltip-arrow { display: none; }
.arrow-top .tooltip-arrow { bottom: -7px; left: 50%; border-top: none; border-left: none; }
.arrow-right .tooltip-arrow { left: -7px; top: 30px; border-bottom: none; border-right: none; }
.arrow-left .tooltip-arrow { right: -7px; top: 30px; border-top: none; border-left: none; }
</style>
