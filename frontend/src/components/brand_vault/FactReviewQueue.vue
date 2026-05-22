<template>
  <div class="frq">
    <div v-if="pendingFacts.length" class="frq-bar">
      <label class="frq-check">
        <input
          type="checkbox"
          :checked="allSelected"
          :indeterminate.prop="someSelected"
          @change="toggleAll"
        />
        <span>{{ allSelected ? 'Deselect all' : 'Select all' }}</span>
      </label>
      <div class="frq-bar-actions">
        <span v-if="selectedIds.size" class="frq-selected">
          {{ selectedIds.size }} selected
        </span>
        <AirButton
          variant="outline"
          size="sm"
          :disabled="!selectedIds.size"
          @click="$emit('bulk-reject', Array.from(selectedIds))"
        >
          Reject {{ selectedIds.size || '' }}
        </AirButton>
        <AirButton
          variant="primary"
          size="sm"
          :disabled="!selectedIds.size"
          @click="bulkApprove"
        >
          Approve {{ selectedIds.size || '' }}
        </AirButton>
      </div>
    </div>

    <div v-if="loading" class="frq-skeleton">
      <div v-for="i in 4" :key="i" class="frq-skel" />
    </div>

    <div v-else-if="!pendingFacts.length" class="frq-empty">
      <div class="frq-empty-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 12l2 2 4-4"/>
          <circle cx="12" cy="12" r="10"/>
        </svg>
      </div>
      <h3>Nothing to review</h3>
      <p>No pending facts. Run a re-scan or import facts to build up the vault.</p>
    </div>

    <div v-else class="frq-list">
      <div
        v-for="fact in pendingFacts"
        :key="fact.id"
        class="frq-row"
        :class="{ 'is-selected': selectedIds.has(fact.id) }"
      >
        <label class="frq-row-check">
          <input
            type="checkbox"
            :checked="selectedIds.has(fact.id)"
            @change="toggle(fact.id)"
          />
        </label>
        <div class="frq-row-body">
          <div class="frq-fact-text">
            <strong>{{ fact.subject }}</strong>
            <span class="frq-pred">{{ fact.predicate }}</span>
            <span>{{ fact.object }}</span>
          </div>
          <div class="frq-row-meta">
            <span class="frq-conf">
              <span class="frq-conf-dot" :class="confidenceClass(fact.confidence)"></span>
              {{ confidencePct(fact.confidence) }}% confidence
            </span>
            <a
              v-if="fact.source_url"
              :href="fact.source_url"
              target="_blank"
              rel="noopener"
              class="frq-source"
            >Source ↗</a>
            <span v-if="fact.product_line" class="frq-tag">{{ fact.product_line }}</span>
            <span v-if="fact.topic" class="frq-tag">{{ fact.topic }}</span>
          </div>
        </div>
        <div class="frq-row-actions">
          <AirButton variant="outline" size="xs" @click="$emit('edit-click', fact)">Edit</AirButton>
          <AirButton variant="ghost" size="xs" @click="$emit('reject', fact)">Reject</AirButton>
          <AirButton variant="primary" size="xs" @click="$emit('approve', fact)">Approve</AirButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  pendingFacts: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  websiteId: { type: String, required: true },
})

const emit = defineEmits(['approve', 'reject', 'edit-click', 'bulk-approve', 'bulk-reject', 'refresh'])

const selectedIds = ref(new Set())

function toggle(id) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  selectedIds.value = next
}

function toggleAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(props.pendingFacts.map((f) => f.id))
  }
}

const allSelected = computed(() =>
  props.pendingFacts.length > 0 &&
  selectedIds.value.size === props.pendingFacts.length,
)
const someSelected = computed(() =>
  selectedIds.value.size > 0 && !allSelected.value,
)

function bulkApprove() {
  emit('bulk-approve', Array.from(selectedIds.value))
  selectedIds.value = new Set()
}

// Drop any ids that have left the pending list (approved / rejected elsewhere).
watch(() => props.pendingFacts, (list) => {
  const ids = new Set(list.map((f) => f.id))
  const next = new Set()
  for (const id of selectedIds.value) if (ids.has(id)) next.add(id)
  selectedIds.value = next
})

function confidencePct(c) {
  const v = Number(c) || 0
  const pct = v <= 1 ? v * 100 : v
  return Math.max(0, Math.min(100, Math.round(pct)))
}
function confidenceClass(c) {
  const p = confidencePct(c)
  if (p >= 75) return 'is-high'
  if (p >= 50) return 'is-mid'
  return 'is-low'
}
</script>

<style scoped>
.frq { display: flex; flex-direction: column; gap: 12px; }

.frq-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
}
.frq-check { display: inline-flex; align-items: center; gap: 8px; font-size: 0.85rem; color: var(--text-secondary); cursor: pointer; }
.frq-bar-actions { display: flex; gap: 8px; align-items: center; }
.frq-selected { font-size: 0.78rem; color: var(--text-muted); }

.frq-list { display: flex; flex-direction: column; gap: 8px; }
.frq-row {
  display: grid;
  grid-template-columns: 22px 1fr auto;
  gap: 14px;
  align-items: start;
  padding: 14px 16px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  transition: border-color 0.15s ease;
}
.frq-row:hover { border-color: var(--border-hover, #d4d4d8); }
.frq-row.is-selected { border-color: var(--brand-accent, #ff6b35); background: rgba(255, 107, 53, 0.04); }
.frq-row-check { display: inline-flex; align-items: center; padding-top: 2px; }
.frq-row-body { min-width: 0; }
.frq-fact-text {
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--text-primary);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.frq-fact-text strong { font-weight: 600; }
.frq-pred { color: var(--text-secondary); }
.frq-row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
  font-size: 0.76rem;
  color: var(--text-muted);
  align-items: center;
}
.frq-conf { display: inline-flex; align-items: center; gap: 6px; }
.frq-conf-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.frq-conf-dot.is-high { background: #10b981; }
.frq-conf-dot.is-mid { background: #f59e0b; }
.frq-conf-dot.is-low { background: #ef4444; }
.frq-source { color: var(--brand-accent, #ff6b35); text-decoration: none; }
.frq-source:hover { text-decoration: underline; }
.frq-tag {
  background: var(--bg-subtle, #fafafa);
  color: var(--text-secondary);
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.frq-row-actions { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }

.frq-skeleton { display: flex; flex-direction: column; gap: 8px; }
.frq-skel {
  height: 84px;
  border-radius: 12px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.frq-empty {
  text-align: center;
  padding: 60px 20px;
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 14px;
  color: var(--text-secondary);
}
.frq-empty-icon {
  display: inline-flex;
  width: 56px; height: 56px;
  align-items: center; justify-content: center;
  border-radius: 14px;
  background: rgba(16, 185, 129, 0.10);
  color: #047857;
  margin-bottom: 12px;
}
.frq-empty h3 { margin: 0 0 4px; font-size: 1.05rem; color: var(--text-primary); }
.frq-empty p { margin: 0; font-size: 0.88rem; }

[data-theme="dark"] .frq-bar,
[data-theme="dark"] .frq-row,
[data-theme="dark"] .frq-skel {
  background: var(--bg-card);
  border-color: var(--border-color);
}
[data-theme="dark"] .frq-tag { background: var(--bg-card-hover); color: var(--text-secondary); }
</style>
