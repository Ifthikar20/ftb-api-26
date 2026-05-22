<template>
  <section v-if="text" class="bvc">
    <header class="bvc-head">
      <span class="bvc-title">Brand Vault check</span>
      <span v-if="loading" class="bvc-spinner" aria-hidden="true"></span>
      <span v-else-if="result" class="bvc-summary">
        <span class="bvc-tally bvc-tally-good"><span class="bvc-dot is-good"></span>{{ result.corroborated.length }} confirmed</span>
        <span v-if="result.contradicted.length" class="bvc-tally bvc-tally-bad"><span class="bvc-dot is-bad"></span>{{ result.contradicted.length }} mismatch{{ result.contradicted.length === 1 ? '' : 'es' }}</span>
        <span class="bvc-tally bvc-tally-mute"><span class="bvc-dot is-mute"></span>{{ result.missed.length }} not mentioned</span>
      </span>
      <span v-else-if="error" class="bvc-error">{{ error }}</span>
    </header>

    <div v-if="result" class="bvc-grid">
      <!-- Brand vault truth -->
      <div class="bvc-col">
        <div class="bvc-col-h">Your brand says</div>
        <ul v-if="!result.total" class="bvc-empty">
          <li>No approved facts in the vault yet — nothing to compare.</li>
        </ul>
        <ul v-else class="bvc-list">
          <li
            v-for="f in displayedFacts"
            :key="f.id"
            class="bvc-fact"
            :class="`is-${f._tag}`"
          >
            <span class="bvc-fact-icon" aria-hidden="true">
              <template v-if="f._tag === 'good'">✓</template>
              <template v-else-if="f._tag === 'bad'">!</template>
              <template v-else>·</template>
            </span>
            <span class="bvc-fact-text">
              <strong>{{ f.subject }}</strong>
              <span class="bvc-fact-pred">{{ f.predicate }}</span>
              <span>{{ f.object }}</span>
            </span>
            <span v-if="f.topic" class="bvc-fact-tag">{{ f.topic }}</span>
          </li>
        </ul>
        <button
          v-if="hiddenMissedCount"
          type="button"
          class="bvc-toggle"
          @click="showAllMissed = !showAllMissed"
        >
          {{ showAllMissed ? `Hide ${hiddenMissedCount}` : `Show ${hiddenMissedCount} more` }}
        </button>
      </div>

      <!-- What the model said -->
      <div class="bvc-col">
        <div class="bvc-col-h">What the model said</div>
        <div class="bvc-response" v-html="highlightedResponse"></div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import brandVaultApi from '@/api/brandVault'

const props = defineProps({
  websiteId: { type: String, required: true },
  text: { type: String, default: '' },
  autorun: { type: Boolean, default: true },
})

const result = ref(null)
const loading = ref(false)
const error = ref('')
const showAllMissed = ref(false)
let pending = null

async function run() {
  const text = (props.text || '').trim()
  if (!text || !props.websiteId) {
    result.value = null
    return
  }
  // Debounce rapid text swaps (e.g. when the user clicks through a
  // few responses quickly) — only the last one fires.
  if (pending) clearTimeout(pending)
  pending = setTimeout(async () => {
    loading.value = true
    error.value = ''
    try {
      const { data } = await brandVaultApi.factCheck(props.websiteId, text)
      result.value = data?.data || data || null
    } catch (e) {
      error.value = e?.displayMessage || 'Vault check failed.'
      result.value = null
    } finally {
      loading.value = false
    }
  }, 180)
}

watch(() => [props.text, props.websiteId], () => {
  if (props.autorun) run()
}, { immediate: true })

onBeforeUnmount(() => { if (pending) clearTimeout(pending) })

// Decorate facts with a UI tag so the template doesn't have to
// reach into three lists. Limit displayed missed facts unless the
// user clicks Show all.
const MISSED_LIMIT = 4
const displayedFacts = computed(() => {
  if (!result.value) return []
  const out = []
  for (const f of result.value.corroborated || []) out.push({ ...f, _tag: 'good' })
  for (const f of result.value.contradicted || []) out.push({ ...f, _tag: 'bad' })
  const missed = result.value.missed || []
  const slice = showAllMissed.value ? missed : missed.slice(0, MISSED_LIMIT)
  for (const f of slice) out.push({ ...f, _tag: 'mute' })
  return out
})
const hiddenMissedCount = computed(() => {
  if (!result.value || showAllMissed.value) return 0
  const m = result.value.missed?.length || 0
  return Math.max(0, m - MISSED_LIMIT)
})

// Highlight any object substring from corroborated facts inside the
// model's response. The Brand Vault check is conservative on the
// backend so we trust its corroborated list here — just wrap each
// match in a span the user can spot.
const highlightedResponse = computed(() => {
  const escaped = escapeHtml(props.text || '')
  if (!result.value?.corroborated?.length) return escaped
  let html = escaped
  // Apply longest objects first so "located in San Francisco" wins
  // over "San Francisco" when both are facts.
  const objects = result.value.corroborated
    .map((f) => (f.object || '').trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
  for (const obj of objects) {
    const re = new RegExp(`(${escapeRegex(obj)})`, 'gi')
    html = html.replace(re, '<mark class="bvc-mark">$1</mark>')
  }
  return html
})

function escapeHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
function escapeRegex(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') }
</script>

<style scoped>
.bvc {
  margin-top: 12px;
  padding: 14px 16px;
  background: var(--bg-subtle, #fafafa);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
}
.bvc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.bvc-title {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.bvc-summary {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  font-size: 0.78rem;
  color: var(--text-secondary);
}
.bvc-tally { display: inline-flex; align-items: center; gap: 6px; }
.bvc-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.bvc-dot.is-good { background: #10b981; }
.bvc-dot.is-bad  { background: #ef4444; }
.bvc-dot.is-mute { background: #cbd5e1; }
.bvc-error { font-size: 0.78rem; color: #b91c1c; }
.bvc-spinner {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid var(--border-color, #e5e7eb);
  border-top-color: var(--text-primary);
  animation: bvc-spin 0.9s linear infinite;
}
@keyframes bvc-spin { to { transform: rotate(360deg); } }

.bvc-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(0, 1.1fr);
  gap: 14px;
}
@media (max-width: 720px) { .bvc-grid { grid-template-columns: 1fr; } }

.bvc-col-h {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.bvc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.bvc-fact {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  gap: 8px;
  align-items: baseline;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--bg-card, #fff);
  font-size: 0.82rem;
  border: 1px solid transparent;
}
.bvc-fact.is-good { border-color: rgba(16, 185, 129, 0.30); }
.bvc-fact.is-bad  { border-color: rgba(239, 68, 68, 0.32); background: rgba(239,68,68,0.04); }
.bvc-fact.is-mute { opacity: 0.78; }
.bvc-fact-icon {
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  font-family: ui-monospace, monospace;
}
.bvc-fact.is-good .bvc-fact-icon { background: rgba(16, 185, 129, 0.16); color: #047857; }
.bvc-fact.is-bad  .bvc-fact-icon { background: rgba(239, 68, 68, 0.16); color: #b91c1c; }
.bvc-fact.is-mute .bvc-fact-icon { background: var(--bg-subtle, #fafafa); color: var(--text-muted); }
.bvc-fact-text {
  display: inline-flex; flex-wrap: wrap; gap: 4px;
  line-height: 1.4;
  color: var(--text-primary);
}
.bvc-fact-text strong { font-weight: 600; }
.bvc-fact-pred { color: var(--text-secondary); }
.bvc-fact-tag {
  align-self: center;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--bg-subtle, #fafafa);
}
.bvc-empty { list-style: none; margin: 0; padding: 6px 10px; font-size: 0.82rem; color: var(--text-muted); }

.bvc-toggle {
  appearance: none;
  background: transparent;
  border: none;
  font: inherit;
  font-size: 0.78rem;
  color: var(--brand-accent, #ff6b35);
  font-weight: 600;
  cursor: pointer;
  margin-top: 4px;
  padding: 4px 2px;
  align-self: flex-start;
}
.bvc-toggle:hover { text-decoration: underline; }

.bvc-response {
  font-size: 0.85rem;
  line-height: 1.55;
  color: var(--text-primary);
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  padding: 10px 12px;
  max-height: 260px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.bvc-response :deep(.bvc-mark) {
  background: rgba(16, 185, 129, 0.18);
  color: inherit;
  padding: 0 2px;
  border-radius: 3px;
}

[data-theme="dark"] .bvc { background: var(--bg-card-hover); border-color: var(--border-color); }
[data-theme="dark"] .bvc-fact { background: var(--bg-card); }
[data-theme="dark"] .bvc-fact.is-bad { background: rgba(239,68,68,0.08); }
[data-theme="dark"] .bvc-response { background: var(--bg-card); border-color: var(--border-color); }
[data-theme="dark"] .bvc-fact-tag { background: var(--bg-card-hover); }
</style>
