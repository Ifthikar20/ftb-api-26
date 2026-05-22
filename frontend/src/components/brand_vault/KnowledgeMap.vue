<template>
  <div class="km">
    <div class="km-filters">
      <button
        type="button"
        class="km-chip"
        :class="{ 'is-on': filter === 'all' }"
        @click="updateFilter('all')"
      >All <span class="km-chip-count">{{ facts.length }}</span></button>
      <button
        v-if="contradictions.length"
        type="button"
        class="km-chip is-warn"
        :class="{ 'is-on': filter === 'contradictions' }"
        @click="updateFilter('contradictions')"
      >Contradictions <span class="km-chip-count">{{ contradictions.length }}</span></button>
      <button
        v-for="pl in productLines"
        :key="pl"
        type="button"
        class="km-chip"
        :class="{ 'is-on': filter === pl }"
        @click="updateFilter(pl)"
      >{{ pl }}</button>
    </div>

    <div v-if="loading" class="km-grid">
      <div v-for="i in 6" :key="i" class="km-skel" />
    </div>

    <div v-else-if="!facts.length" class="km-empty">
      <h3>Nothing here yet</h3>
      <p>Approve facts from the Review queue to populate the map.</p>
    </div>

    <div v-else class="km-grid">
      <div
        v-for="fact in facts"
        :key="fact.id"
        class="km-card"
        :class="{ 'is-conflict': conflictedIds.has(fact.id) }"
        @click="$emit('open-detail', fact)"
      >
        <div class="km-card-status">
          <span class="km-pill" :class="`is-${fact.status}`">
            {{ fact.status === 'auto' ? 'Auto' : 'Approved' }}
          </span>
          <span v-if="conflictedIds.has(fact.id)" class="km-pill is-warn">Conflict</span>
        </div>
        <div class="km-card-text">
          <strong>{{ fact.subject }}</strong>
          <span class="km-pred">{{ fact.predicate }}</span>
          <span>{{ fact.object }}</span>
        </div>
        <div class="km-card-meta">
          <span v-if="fact.product_line" class="km-tag">{{ fact.product_line }}</span>
          <span v-if="fact.topic" class="km-tag">{{ fact.topic }}</span>
          <span class="km-conf">{{ confidencePct(fact.confidence) }}% conf</span>
        </div>
        <div class="km-card-actions" @click.stop>
          <AirButton variant="ghost" size="xs" @click="$emit('edit-click', fact)">Edit</AirButton>
          <AirButton variant="ghost" size="xs" @click="$emit('reject', fact)">Archive</AirButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  facts: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  productLines: { type: Array, default: () => [] },
  topics: { type: Array, default: () => [] },
  contradictions: { type: Array, default: () => [] },
  filter: { type: String, default: 'all' },
  websiteId: { type: String, required: true },
})

const emit = defineEmits(['update:filter', 'approve', 'reject', 'edit-click', 'open-detail'])

function updateFilter(val) {
  emit('update:filter', val)
}

const conflictedIds = computed(() => {
  const s = new Set()
  for (const c of props.contradictions) {
    for (const f of c.facts || []) s.add(f.id)
  }
  return s
})

function confidencePct(c) {
  const v = Number(c) || 0
  const pct = v <= 1 ? v * 100 : v
  return Math.max(0, Math.min(100, Math.round(pct)))
}
</script>

<style scoped>
.km { display: flex; flex-direction: column; gap: 14px; }

.km-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.km-chip {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 999px;
  background: var(--bg-card, #fff);
  font-size: 0.8rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.km-chip:hover { border-color: var(--border-hover, #d4d4d8); }
.km-chip.is-on {
  background: var(--text-primary);
  color: var(--bg-card, #fff);
  border-color: var(--text-primary);
}
.km-chip.is-warn { color: #b45309; border-color: rgba(245,158,11,0.4); }
.km-chip.is-warn.is-on { background: #f59e0b; color: #fff; border-color: #f59e0b; }
.km-chip-count {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 1px 7px;
  background: rgba(0,0,0,0.06);
  border-radius: 999px;
}
.km-chip.is-on .km-chip-count { background: rgba(255,255,255,0.18); }

.km-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.km-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.km-card:hover {
  border-color: var(--border-hover, #d4d4d8);
  box-shadow: 0 6px 18px -10px rgba(20, 23, 24, 0.12);
}
.km-card.is-conflict { border-color: rgba(245,158,11,0.55); background: rgba(245,158,11,0.04); }
.km-card-status { display: flex; gap: 6px; }
.km-pill {
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 999px;
}
.km-pill.is-approved { background: rgba(16,185,129,0.14); color: #047857; }
.km-pill.is-auto { background: rgba(91,141,239,0.14); color: #1d4ed8; }
.km-pill.is-warn { background: rgba(245,158,11,0.16); color: #b45309; }
.km-card-text {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-primary);
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.km-card-text strong { font-weight: 600; }
.km-pred { color: var(--text-secondary); }
.km-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 0.72rem;
  color: var(--text-muted);
  align-items: center;
}
.km-tag {
  background: var(--bg-subtle, #fafafa);
  padding: 1px 7px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.km-conf { font-variant-numeric: tabular-nums; }
.km-card-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
  border-top: 1px solid var(--border-color, #e5e7eb);
  padding-top: 8px;
}

.km-skel {
  height: 140px;
  border-radius: 12px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.km-empty {
  text-align: center;
  padding: 60px 20px;
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 14px;
  color: var(--text-secondary);
}
.km-empty h3 { margin: 0 0 4px; color: var(--text-primary); font-size: 1.05rem; }
.km-empty p { margin: 0; font-size: 0.88rem; }

[data-theme="dark"] .km-chip,
[data-theme="dark"] .km-card,
[data-theme="dark"] .km-skel {
  background: var(--bg-card);
  border-color: var(--border-color);
}
[data-theme="dark"] .km-chip-count { background: rgba(255,255,255,0.06); }
[data-theme="dark"] .km-tag { background: var(--bg-card-hover); color: var(--text-secondary); }
[data-theme="dark"] .km-card-actions { border-color: var(--border-color); }
</style>
