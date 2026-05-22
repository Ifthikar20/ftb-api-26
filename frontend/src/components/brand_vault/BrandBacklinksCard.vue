<template>
  <div class="bbl-card">
    <div class="bbl-head">
      <h3 class="bbl-title">Find every place your brand was mentioned.</h3>
      <p class="bbl-sub">
        We watch which third-party sources Claude, GPT-4, Gemini, and Perplexity
        cite whenever they talk about <strong>{{ brandName || 'your brand' }}</strong>.
      </p>
    </div>

    <div v-if="loading" class="bbl-list">
      <div v-for="i in 3" :key="i" class="bbl-skel" />
    </div>

    <div v-else-if="!items.length" class="bbl-empty">
      No third-party mentions detected yet. Run an audit on the LLM Dashboard
      to surface where models cite your brand from.
    </div>

    <div v-else class="bbl-list">
      <div
        v-for="row in visible"
        :key="row.apex_domain"
        class="bbl-row"
      >
        <img
          :src="faviconFor(row.apex_domain)"
          :alt="row.domain"
          class="bbl-favicon"
          @error="onFaviconError($event, row)"
        />
        <div class="bbl-row-name">
          <a :href="`https://${row.domain}`" target="_blank" rel="noopener">{{ row.domain }}</a>
          <span v-if="row.recent" class="bbl-pill bbl-pill-new">JUST DETECTED</span>
          <span v-else-if="row.is_competitor_source" class="bbl-pill bbl-pill-comp">COMPETITOR</span>
        </div>
        <div class="bbl-row-count">
          {{ row.mention_count }}<span class="bbl-row-unit"> mention{{ row.mention_count === 1 ? '' : 's' }}</span>
        </div>
      </div>

      <div class="bbl-footer">
        <span>Total mentions across {{ items.length }} {{ items.length === 1 ? 'source' : 'sources' }}</span>
        <strong>{{ totalMentions }}</strong>
      </div>

      <button
        v-if="items.length > limit"
        type="button"
        class="bbl-toggle"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'Show top 5' : `Show all ${items.length} sources` }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  totalMentions: { type: Number, default: 0 },
  brandName: { type: String, default: '' },
})

const expanded = ref(false)
const limit = 5
const visible = computed(() => expanded.value ? props.items : props.items.slice(0, limit))

function faviconFor(domain) {
  if (!domain) return ''
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`
}
function onFaviconError(ev, row) {
  // Inline SVG fallback: first letter of the apex domain on a neutral chip.
  const letter = (row.apex_domain || row.domain || '?').charAt(0).toUpperCase()
  const svg = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Crect width='32' height='32' rx='8' fill='%23e5e7eb'/%3E%3Ctext x='16' y='21' text-anchor='middle' font-size='14' font-family='sans-serif' fill='%236b7280' font-weight='600'%3E${letter}%3C/text%3E%3C/svg%3E`
  ev.target.src = svg
}
</script>

<style scoped>
.bbl-card {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 16px;
  padding: 24px;
}
.bbl-head { margin-bottom: 18px; }
.bbl-title {
  margin: 0 0 6px;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}
.bbl-sub {
  margin: 0;
  font-size: 0.92rem;
  color: var(--text-secondary);
  line-height: 1.5;
}
.bbl-sub strong { color: var(--text-primary); font-weight: 600; }

.bbl-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 14px;
  background: var(--bg-card, #fff);
  padding: 4px 4px;
}
.bbl-row {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.bbl-row:last-of-type { border-bottom: none; }
.bbl-favicon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  object-fit: cover;
  background: var(--bg-subtle, #fafafa);
}
.bbl-row-name {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 1rem;
  color: var(--text-primary);
}
.bbl-row-name a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
  border-bottom: 1px solid transparent;
}
.bbl-row-name a:hover { border-bottom-color: var(--text-muted); }
.bbl-row-count {
  font-size: 0.95rem;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.bbl-row-unit { color: var(--text-muted); font-weight: 400; }

.bbl-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  white-space: nowrap;
  border: 1px solid;
}
.bbl-pill-new {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.32);
  color: #b45309;
}
.bbl-pill-comp {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.30);
  color: #4338ca;
}

.bbl-footer {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 12px 16px 8px;
  margin-top: 4px;
  border-top: 1px solid var(--border-color, #e5e7eb);
  font-size: 0.88rem;
  color: var(--text-muted);
}
.bbl-footer strong {
  font-size: 1.05rem;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.bbl-toggle {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--brand-accent, #ff6b35);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 6px 16px 10px;
  cursor: pointer;
  text-align: left;
}
.bbl-toggle:hover { text-decoration: underline; }

.bbl-skel {
  height: 52px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  background:
    linear-gradient(90deg, transparent 32%, rgba(255,255,255,0.4) 50%, transparent 68%),
    var(--bg-subtle, #fafafa);
  background-size: 200% 100%;
  animation: bbl-shimmer 1.4s linear infinite;
}
.bbl-skel:last-of-type { border-bottom: none; }
@keyframes bbl-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.bbl-empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 0.88rem;
  color: var(--text-muted);
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 12px;
}

[data-theme="dark"] .bbl-card,
[data-theme="dark"] .bbl-list { background: var(--bg-card); border-color: var(--border-color); }
[data-theme="dark"] .bbl-row { border-color: var(--border-color); }
[data-theme="dark"] .bbl-footer { border-color: var(--border-color); }
[data-theme="dark"] .bbl-favicon { background: var(--bg-card-hover); }
</style>
