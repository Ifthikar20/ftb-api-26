<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  stable: { type: Boolean, default: false },
  components: { type: Object, default: () => ({}) },
  expandable: { type: Boolean, default: true },
})

const expanded = ref(false)

const pct = computed(() => Math.max(0, Math.min(100, Math.round((props.score || 0) * 100))))

const tone = computed(() => {
  if (!props.stable) return 'untested'
  if (props.score >= 0.7) return 'success'
  if (props.score >= 0.4) return 'warning'
  return 'danger'
})

const label = computed(() => {
  if (!props.stable) return 'Untested'
  return `${pct.value}%`
})

function toggle() {
  if (props.expandable) expanded.value = !expanded.value
}

const breakdown = computed(() => {
  const c = props.components || {}
  return [
    { key: 'visibility_hit_rate', label: 'Visibility', value: Number(c.visibility_hit_rate || 0) },
    { key: 'citation_yield', label: 'Citations', value: Number(c.citation_yield || 0) },
    { key: 'claim_yield', label: 'Claims', value: Number(c.claim_yield || 0) },
    { key: 'coverage_breadth', label: 'Breadth', value: Number(c.coverage_breadth || 0) },
  ]
})
</script>

<template>
  <div class="em-wrap" :class="`em-${tone}`">
    <button
      type="button"
      class="em-bar"
      :class="{ 'em-untested': !stable, 'em-clickable': expandable }"
      :title="stable ? `Effectiveness ${pct}%` : 'Needs 3+ runs to give a score'"
      @click.stop="toggle"
    >
      <span class="em-fill" :style="{ width: stable ? pct + '%' : '0%' }"></span>
      <span class="em-label">{{ label }}</span>
    </button>
    <div v-if="expanded && stable" class="em-breakdown">
      <div v-for="b in breakdown" :key="b.key" class="em-row">
        <span class="em-row-label">{{ b.label }}</span>
        <span class="em-row-bar">
          <span class="em-row-fill" :style="{ width: Math.round(b.value * 100) + '%' }"></span>
        </span>
        <span class="em-row-val">{{ Math.round(b.value * 100) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.em-wrap {
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
  min-width: 92px;
}
.em-bar {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 92px;
  height: 18px;
  padding: 0;
  border-radius: 9999px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  overflow: hidden;
  cursor: default;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}
.em-clickable { cursor: pointer; }
.em-untested {
  border-style: dashed;
  color: var(--text-muted);
  background: transparent;
}
.em-fill {
  position: absolute;
  inset: 0 auto 0 0;
  height: 100%;
  background: var(--brand-accent);
  opacity: 0.18;
  transition: width 200ms ease-out;
}
.em-success .em-fill { background: var(--color-success, #16a34a); opacity: 0.22; }
.em-warning .em-fill { background: var(--color-warning, #f59e0b); opacity: 0.22; }
.em-danger .em-fill  { background: var(--color-danger, #dc2626); opacity: 0.18; }
.em-label {
  position: relative;
  z-index: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
}
.em-breakdown {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  border-radius: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}
.em-row {
  display: grid;
  grid-template-columns: 60px 1fr 22px;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--text-secondary);
}
.em-row-bar {
  height: 4px;
  border-radius: 9999px;
  background: var(--border-color);
  overflow: hidden;
}
.em-row-fill {
  display: block;
  height: 100%;
  background: var(--brand-accent);
}
.em-row-val {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}
</style>
