<template>
  <!--
    Prompt × Provider heatmap. Pure CSS grid — no Chart.js. Each cell
    shows the brand's mention rank for one (prompt, provider) pair,
    coloured green for top-3 down through neutral / miss / API error.
    Hovering a cell surfaces the full prompt text and the provider's
    raw response length so the user can spot which provider is being
    chatty vs sparse.
  -->
  <div v-if="hasData" class="ph-card">
    <div class="ph-header">
      <h3 class="ph-title">Where you rank, prompt by provider</h3>
      <div class="ph-legend">
        <span class="ph-legend-item"><i class="ph-cell ph-rank-1"></i>#1–3</span>
        <span class="ph-legend-item"><i class="ph-cell ph-rank-2"></i>#4–7</span>
        <span class="ph-legend-item"><i class="ph-cell ph-rank-3"></i>#8+</span>
        <span class="ph-legend-item"><i class="ph-cell ph-miss"></i>Not mentioned</span>
        <span class="ph-legend-item"><i class="ph-cell ph-fail"></i>Error</span>
      </div>
    </div>

    <div class="ph-scroll">
      <div class="ph-grid" :style="gridStyle">
        <!-- Header row: provider labels -->
        <div class="ph-prompt-cell ph-corner"></div>
        <div
          v-for="p in providers"
          :key="p"
          class="ph-prov-cell"
          :title="p"
        >
          <span class="ph-prov-dot" :style="{ background: providerColor(p) }"></span>
          {{ providerLabel(p) }}
        </div>

        <!-- One row per prompt -->
        <template v-for="(row, i) in rows" :key="row.prompt">
          <div class="ph-prompt-cell" :title="row.prompt">
            <span class="ph-prompt-num">{{ i + 1 }}</span>
            <span class="ph-prompt-text">{{ row.prompt }}</span>
          </div>
          <div
            v-for="p in providers"
            :key="row.prompt + p"
            class="ph-cell"
            :class="cellClass(row.cells[p])"
            :title="cellTitle(row.cells[p])"
          >
            <span v-if="cellLabel(row.cells[p])">{{ cellLabel(row.cells[p]) }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  results: { type: Array, default: () => [] },
  providerLabel: { type: Function, default: (p) => p },
  providerColor: { type: Function, default: () => '#888' },
})

const providers = computed(() => {
  // Stable provider ordering so columns don't reshuffle between renders.
  const seen = new Set()
  for (const r of props.results) if (r.provider) seen.add(r.provider)
  return Array.from(seen).sort()
})

const rows = computed(() => {
  // Group results by prompt. Each row gets one cell per provider.
  // Limited to the most recent 25 unique prompts so the grid never
  // grows unbounded — older audits with 50-prompt runs still render.
  const byPrompt = new Map()
  for (const r of props.results) {
    const k = (r.prompt || '').trim()
    if (!k) continue
    let bucket = byPrompt.get(k)
    if (!bucket) {
      bucket = { prompt: k, cells: {} }
      byPrompt.set(k, bucket)
    }
    bucket.cells[r.provider] = r
  }
  return Array.from(byPrompt.values()).slice(-25)
})

const hasData = computed(() => rows.value.length > 0 && providers.value.length > 0)

const gridStyle = computed(() => ({
  gridTemplateColumns: `minmax(220px, 1.6fr) repeat(${providers.value.length}, minmax(86px, 1fr))`,
}))

function cellClass(cell) {
  if (!cell) return 'ph-empty'
  if (!cell.query_succeeded) return 'ph-fail'
  if (!cell.is_mentioned) return 'ph-miss'
  const r = cell.mention_rank
  if (r != null && r <= 3) return 'ph-rank-1'
  if (r != null && r <= 7) return 'ph-rank-2'
  return 'ph-rank-3'
}

function cellLabel(cell) {
  if (!cell || !cell.query_succeeded) return ''
  if (!cell.is_mentioned) return '—'
  return cell.mention_rank ? `#${cell.mention_rank}` : '✓'
}

function cellTitle(cell) {
  if (!cell) return 'No result'
  if (!cell.query_succeeded) return `Error: ${cell.error_message || 'API failed'}`
  if (!cell.is_mentioned) return 'Not mentioned in this response'
  const len = (cell.response_text || '').length
  return `Rank #${cell.mention_rank || '?'} — ${len.toLocaleString()} chars in response`
}
</script>

<style scoped>
.ph-card {
  background: var(--bg-secondary, #fff);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}
.ph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.ph-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.ph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
}
.ph-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ph-legend i.ph-cell {
  width: 14px; height: 14px;
  border-radius: 4px;
  display: inline-block;
}

.ph-scroll {
  overflow-x: auto;
  overflow-y: hidden;
}
.ph-grid {
  display: grid;
  gap: 4px;
  min-width: 100%;
}

.ph-corner {
  border-bottom: 1px solid var(--border-color);
}
.ph-prov-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ph-prov-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  display: inline-block;
}

.ph-prompt-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ph-prompt-num {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-muted);
  flex-shrink: 0;
}
.ph-prompt-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ph-cell {
  border-radius: 6px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  background: var(--bg-base, #f4f4f5);
  border: 1px solid transparent;
  transition: transform 0.15s ease, border-color 0.15s ease;
  cursor: default;
}
.ph-cell:hover { transform: scale(1.04); border-color: rgba(0, 0, 0, 0.18); }

.ph-rank-1 { background: rgba(16, 185, 129, 0.85); color: #fff; }
.ph-rank-2 { background: rgba(16, 185, 129, 0.45); color: #064e3b; }
.ph-rank-3 { background: rgba(16, 185, 129, 0.2); color: #064e3b; }
.ph-miss   { background: var(--bg-base, #f4f4f5); color: var(--text-muted); }
.ph-fail   { background: rgba(239, 68, 68, 0.18); color: #b91c1c; }
.ph-empty  { background: transparent; }
</style>
