<template>
  <div class="usage-card">
    <div class="usage-card-header">
      <div>
        <div class="usage-card-label">Voice agent usage</div>
        <div class="usage-card-period">{{ formatPeriod(current.year_month) }} · resets in {{ daysUntilReset }}d</div>
      </div>
      <button class="btn btn-ghost btn-xs" @click="$emit('refresh')" :disabled="loading">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <div class="usage-card-main">
      <div class="usage-minutes">
        <span class="usage-minutes-value">{{ current.billable_minutes || 0 }}</span>
        <span v-if="current.plan_limit_minutes" class="usage-minutes-limit">/ {{ current.plan_limit_minutes.toLocaleString() }}</span>
        <span class="usage-minutes-unit">minutes</span>
      </div>

      <div v-if="current.plan_limit_minutes" class="usage-bar">
        <div
          class="usage-bar-fill"
          :class="barClass"
          :style="{ width: Math.min(current.plan_limit_pct || 0, 100) + '%' }"
        ></div>
      </div>
      <div v-if="current.plan_limit_minutes" class="usage-pct">{{ current.plan_limit_pct }}% of plan</div>
    </div>

    <div class="usage-stats">
      <div class="usage-stat">
        <div class="usage-stat-label">Calls</div>
        <div class="usage-stat-value">{{ current.total_calls || 0 }}</div>
        <div class="usage-stat-sub">{{ current.inbound_calls || 0 }} in · {{ current.outbound_calls || 0 }} out</div>
      </div>
      <div class="usage-stat">
        <div class="usage-stat-label">Est. cost</div>
        <div class="usage-stat-value">${{ formatCost(current.estimated_cost_usd) }}</div>
        <div class="usage-stat-sub">{{ avgCostPerCall }}</div>
      </div>
      <div class="usage-stat">
        <div class="usage-stat-label">LLM tokens</div>
        <div class="usage-stat-value">{{ formatTokens(totalTokens) }}</div>
        <div class="usage-stat-sub">in + out</div>
      </div>
      <div class="usage-stat">
        <div class="usage-stat-label">Last 6 mo</div>
        <svg class="usage-spark" viewBox="0 0 120 32" preserveAspectRatio="none">
          <polyline
            v-if="sparkPoints"
            :points="sparkPoints"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  current: { type: Object, default: () => ({}) },
  history: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
defineEmits(['refresh'])

const totalTokens = computed(() => (props.current.llm_input_tokens || 0) + (props.current.llm_output_tokens || 0))

const avgCostPerCall = computed(() => {
  const calls = props.current.total_calls || 0
  if (!calls) return 'no calls yet'
  const cost = parseFloat(props.current.estimated_cost_usd || 0)
  return `$${(cost / calls).toFixed(3)} / call`
})

const barClass = computed(() => {
  const pct = props.current.plan_limit_pct || 0
  if (pct >= 95) return 'usage-bar-danger'
  if (pct >= 80) return 'usage-bar-warn'
  return 'usage-bar-ok'
})

const daysUntilReset = computed(() => {
  const now = new Date()
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  return Math.max(0, Math.ceil((next - now) / 86_400_000))
})

const sparkPoints = computed(() => {
  if (!props.history.length) return null
  const minutes = props.history.map(h => h.billable_minutes || 0)
  const max = Math.max(...minutes, 1)
  const step = 120 / Math.max(props.history.length - 1, 1)
  return minutes
    .map((m, i) => `${(i * step).toFixed(1)},${(28 - (m / max) * 24).toFixed(1)}`)
    .join(' ')
})

function formatPeriod(ym) {
  if (!ym) return ''
  const [y, m] = ym.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleString('en-US', { month: 'long', year: 'numeric' })
}
function formatCost(v) {
  return parseFloat(v || 0).toFixed(2)
}
function formatTokens(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k'
  return String(n)
}
</script>

<style scoped>
.usage-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.usage-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.usage-card-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}
.usage-card-period {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}
.usage-card-main { margin-bottom: 16px; }
.usage-minutes {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.usage-minutes-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--text-primary);
}
.usage-minutes-limit { font-size: 18px; color: var(--text-muted); }
.usage-minutes-unit { font-size: 13px; color: var(--text-muted); margin-left: 4px; }

.usage-bar {
  margin-top: 10px;
  height: 6px;
  background: var(--bg-surface);
  border-radius: 999px;
  overflow: hidden;
}
.usage-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}
.usage-bar-ok { background: #22c55e; }
.usage-bar-warn { background: #f59e0b; }
.usage-bar-danger { background: #ef4444; }
.usage-pct { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.usage-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.usage-stat-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}
.usage-stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: 2px;
}
.usage-stat-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.usage-spark { width: 100%; height: 32px; color: var(--brand-primary); margin-top: 4px; }

@media (max-width: 640px) {
  .usage-stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
