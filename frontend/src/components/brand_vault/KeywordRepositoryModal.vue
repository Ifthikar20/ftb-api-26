<template>
  <BaseModal v-model="modelOpen" title="" :wide="true">
    <div class="krm">
      <header class="krm-head">
        <div>
          <h2 class="krm-title">Keywords</h2>
          <p class="krm-sub">
            {{ totalMentions }} of {{ totalMentions }} facts analysed
          </p>
        </div>
        <div class="krm-head-actions">
          <button class="krm-btn-soft" type="button" @click="onExport">Export</button>
        </div>
      </header>

      <div class="krm-toolbar">
        <input
          v-model="search"
          type="search"
          class="krm-search"
          placeholder="Filter keywords…"
        />
        <div class="krm-sort">
          <label>
            Sort:
            <select v-model="sortBy" class="krm-sort-select">
              <option value="mentions">Mentions</option>
              <option value="topic">A → Z</option>
              <option value="confidence">Confidence</option>
              <option value="recent">Most recent</option>
            </select>
          </label>
        </div>
      </div>

      <div class="krm-table-wrap">
        <table class="krm-table">
          <thead>
            <tr>
              <th style="width: 28px"></th>
              <th>Category</th>
              <th style="width: 96px">AI Summary</th>
              <th style="width: 130px">Avg. Confidence</th>
              <th style="width: 110px" class="num">Mentions</th>
              <th style="width: 130px" class="num">Share</th>
              <th style="width: 130px">Chart</th>
              <th style="width: 36px"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in visibleRows"
              :key="row.topic"
            >
              <td class="num">{{ i + 1 }}</td>
              <td class="krm-cat">{{ row.topic }}</td>
              <td>
                <button class="krm-analyze" type="button" @click="onAnalyze(row)">Analyze</button>
              </td>
              <td>
                <span class="krm-star">★</span>
                {{ formatConfidence(row.avg_confidence) }}
              </td>
              <td class="num">{{ row.mention_count.toLocaleString() }}</td>
              <td class="num">{{ row.share_pct }}%</td>
              <td>
                <KeywordSparkline :data="row.timeline" :width="110" :height="32" />
              </td>
              <td class="num">
                <div class="krm-menu-wrap" @click.stop>
                  <button
                    class="krm-menu-trigger"
                    type="button"
                    :aria-expanded="openMenu === row.topic"
                    @click="openMenu = openMenu === row.topic ? null : row.topic"
                  >⋯</button>
                  <div v-if="openMenu === row.topic" class="krm-menu">
                    <button type="button" @click="onEdit(row)"><span aria-hidden="true">✎</span> Edit</button>
                    <button type="button" class="is-danger" @click="onDelete(row)"><span aria-hidden="true">🗑</span> Delete topic</button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!visibleRows.length" class="krm-empty">
          No keywords match the current filter.
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import KeywordSparkline from './KeywordSparkline.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
  totalMentions: { type: Number, default: 0 },
})
const emit = defineEmits(['update:open', 'analyze', 'edit', 'delete'])

const modelOpen = computed({
  get: () => props.open,
  set: (v) => emit('update:open', v),
})

const search = ref('')
const sortBy = ref('mentions')
const openMenu = ref(null)

watch(() => props.open, (o) => { if (!o) { search.value = ''; openMenu.value = null } })

const visibleRows = computed(() => {
  let rows = [...props.items]
  const q = search.value.trim().toLowerCase()
  if (q) rows = rows.filter((r) => (r.topic || '').toLowerCase().includes(q))
  switch (sortBy.value) {
    case 'topic':
      rows.sort((a, b) => (a.topic || '').localeCompare(b.topic || ''))
      break
    case 'confidence':
      rows.sort((a, b) => (b.avg_confidence || 0) - (a.avg_confidence || 0))
      break
    case 'recent':
      rows.sort((a, b) => new Date(b.last_seen || 0) - new Date(a.last_seen || 0))
      break
    case 'mentions':
    default:
      rows.sort((a, b) => (b.mention_count || 0) - (a.mention_count || 0))
  }
  return rows
})

function formatConfidence(c) {
  const v = Number(c) || 0
  const display = v <= 1 ? v * 5 : v
  return display.toFixed(1)
}

function onAnalyze(row) { emit('analyze', row) }
function onEdit(row) { openMenu.value = null; emit('edit', row) }
function onDelete(row) { openMenu.value = null; emit('delete', row) }

function onExport() {
  const rows = [['rank', 'topic', 'mentions', 'share_pct', 'avg_confidence', 'last_seen']]
  visibleRows.value.forEach((r, i) => {
    rows.push([i + 1, r.topic, r.mention_count, r.share_pct, r.avg_confidence, r.last_seen || ''])
  })
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `keywords-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Close any open row menu when the user clicks outside.
function _closeMenuOnDocClick() { openMenu.value = null }
watch(modelOpen, (open) => {
  if (open) document.addEventListener('click', _closeMenuOnDocClick)
  else document.removeEventListener('click', _closeMenuOnDocClick)
})
</script>

<style scoped>
.krm { display: flex; flex-direction: column; gap: 16px; padding: 4px 8px 16px; }
.krm-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}
.krm-title { margin: 0; font-size: 1.5rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.krm-sub { margin: 4px 0 0; font-size: 0.85rem; color: var(--text-muted); }
.krm-head-actions { display: flex; gap: 8px; }
.krm-btn-soft {
  appearance: none;
  border: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-card, #fff);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 500;
  padding: 7px 14px;
  border-radius: 999px;
  cursor: pointer;
}
.krm-btn-soft:hover { border-color: var(--text-primary); }

.krm-toolbar { display: flex; align-items: center; gap: 12px; }
.krm-search {
  flex: 1;
  border: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-input, #fff);
  border-radius: 999px;
  padding: 8px 14px;
  font: inherit;
  font-size: 0.85rem;
  color: var(--text-primary);
}
.krm-search:focus { outline: none; border-color: var(--brand-accent, #ff6b35); box-shadow: 0 0 0 3px rgba(255,107,53,0.18); }
.krm-sort { font-size: 0.82rem; color: var(--text-muted); }
.krm-sort-select {
  appearance: none;
  background: var(--bg-input, #fff)
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%236b7280' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E")
    no-repeat right 10px center;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  padding: 6px 28px 6px 10px;
  font: inherit;
  font-size: 0.82rem;
  color: var(--text-primary);
  margin-left: 6px;
}

.krm-table-wrap {
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 14px;
  overflow: hidden;
  background: var(--bg-card, #fff);
}
.krm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.krm-table th {
  text-align: left;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  padding: 14px 16px;
  background: var(--bg-subtle, #fafafa);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.krm-table th.num { text-align: right; }
.krm-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  color: var(--text-primary);
  vertical-align: middle;
}
.krm-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.krm-table tbody tr:last-child td { border-bottom: none; }
.krm-table tbody tr:hover { background: var(--bg-subtle, #fafafa); }
.krm-cat { font-weight: 500; text-transform: capitalize; }

.krm-analyze {
  appearance: none;
  border: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-card, #fff);
  border-radius: 999px;
  padding: 5px 16px;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
}
.krm-analyze:hover { border-color: var(--text-primary); }

.krm-star { color: #f59e0b; margin-right: 4px; }

.krm-menu-wrap { position: relative; display: inline-block; }
.krm-menu-trigger {
  appearance: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  color: var(--text-muted);
}
.krm-menu-trigger:hover { background: var(--bg-subtle, #fafafa); color: var(--text-primary); }
.krm-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  min-width: 168px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  box-shadow: 0 12px 24px -8px rgba(20, 23, 24, 0.16);
  padding: 6px;
  z-index: 5;
  text-align: left;
}
.krm-menu button {
  appearance: none;
  background: transparent;
  border: none;
  font: inherit;
  font-size: 0.85rem;
  color: var(--text-primary);
  padding: 8px 10px;
  border-radius: 6px;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.krm-menu button:hover { background: var(--bg-subtle, #fafafa); }
.krm-menu button.is-danger { color: #b91c1c; }
.krm-menu button.is-danger:hover { background: rgba(239, 68, 68, 0.10); }

.krm-empty { padding: 32px 20px; text-align: center; font-size: 0.88rem; color: var(--text-muted); }

[data-theme="dark"] .krm-table-wrap,
[data-theme="dark"] .krm-table td,
[data-theme="dark"] .krm-analyze,
[data-theme="dark"] .krm-btn-soft,
[data-theme="dark"] .krm-menu { background: var(--bg-card); border-color: var(--border-color); color: var(--text-primary); }
[data-theme="dark"] .krm-table th { background: var(--bg-card-hover); border-color: var(--border-color); color: var(--text-muted); }
[data-theme="dark"] .krm-table td { border-color: var(--border-color); }
[data-theme="dark"] .krm-table tbody tr:hover { background: var(--bg-card-hover); }
[data-theme="dark"] .krm-search { background: var(--bg-input); border-color: var(--border-color); color: var(--text-primary); }
[data-theme="dark"] .krm-sort-select { background-color: var(--bg-input); border-color: var(--border-color); color: var(--text-primary); }
</style>
