<template>
  <div class="keywords-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Keyword Rank Tracker</h1>
        <p class="page-subtitle">Monitor your search rankings daily.</p>
      </div>
      <button class="btn btn-primary" @click="showAddModal = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Track Keyword
      </button>
    </div>

    <div v-if="loading" class="loading-state">Loading keywords...</div>
    <template v-else>
      <!-- Summary Stats -->
      <div class="kw-stats">
        <div class="stat-pill">
          <span class="stat-label">Keywords Tracked</span>
          <span class="stat-value">{{ keywords.length }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Avg. Position</span>
          <span class="stat-value">{{ avgPosition }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label pill-up">Improved</span>
          <span class="stat-value" style="color:var(--color-success)">{{ improved }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label pill-down">Declined</span>
          <span class="stat-value" style="color:var(--color-danger)">{{ declined }}</span>
        </div>
      </div>

      <!-- Keywords Table -->
      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th>Keyword</th>
              <th class="text-center">Position</th>
              <th class="text-center">Change</th>
              <th class="text-center">Best</th>
              <th class="text-center">Volume</th>
              <th class="text-center">Difficulty</th>
              <th class="text-center">30d Trend</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="kw in keywords" :key="kw.id" class="kw-row" @click="toggleHistory(kw)">
              <td>
                <div class="kw-name">{{ kw.keyword }}</div>
                <div class="kw-url">{{ cleanUrl(kw.target_url) }}</div>
              </td>
              <td class="text-center">
                <span class="rank-badge" :class="rankClass(kw.current_rank)">{{ kw.current_rank || '--' }}</span>
              </td>
              <td class="text-center">
                <span v-if="kw.rank_change > 0" class="change-up">+{{ kw.rank_change }}</span>
                <span v-else-if="kw.rank_change < 0" class="change-down">{{ kw.rank_change }}</span>
                <span v-else class="change-flat">--</span>
              </td>
              <td class="text-center font-semibold">{{ kw.best_rank || '--' }}</td>
              <td class="text-center">{{ (kw.search_volume || 0).toLocaleString() }}</td>
              <td class="text-center">
                <div class="diff-bar-wrap">
                  <div class="diff-bar" :style="{ width: kw.difficulty + '%' }" :class="diffClass(kw.difficulty)"></div>
                  <span class="diff-num">{{ kw.difficulty }}</span>
                </div>
              </td>
              <td class="text-center">
                <!-- Mini sparkline -->
                <svg v-if="kw._history" width="100" height="28" class="sparkline">
                  <polyline :points="sparklinePoints(kw._history)" fill="none" stroke="var(--brand-accent)" stroke-width="1.5"/>
                </svg>
                <span v-else class="text-muted text-sm">Click to load</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Expanded Chart -->
      <div v-if="expandedKw" class="card" style="margin-top:20px">
        <div class="card-header">
          <h3 class="card-title">Rank History: {{ expandedKw.keyword }}</h3>
          <span class="text-sm text-muted">Last 30 days</span>
        </div>
        <div class="rank-chart-wrap">
          <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="rank-chart">
            <!-- Y-axis labels (rank numbers — lower is better so inverted) -->
            <text v-for="r in yLabels" :key="r" x="30" :y="rankToY(r) + 4" class="chart-label">{{ r }}</text>
            <line v-for="r in yLabels" :key="'g'+r" x1="45" :y1="rankToY(r)" :x2="chartW-10" :y2="rankToY(r)" class="grid-line"/>

            <!-- Area fill -->
            <path :d="areaPath" class="chart-area"/>
            <!-- Line -->
            <polyline :points="chartLine" fill="none" stroke="var(--brand-accent)" stroke-width="2"/>
            <!-- Dots -->
            <circle v-for="(pt, i) in chartPoints" :key="i"
              :cx="pt.x" :cy="pt.y" r="3"
              fill="var(--brand-accent)" stroke="var(--bg-card)" stroke-width="1.5"
              class="chart-dot"
            />
            <!-- X-axis labels -->
            <text v-for="(pt, i) in chartPoints" :key="'x'+i"
              :x="pt.x" :y="chartH - 2"
              class="chart-label" text-anchor="middle"
              v-if="i % 5 === 0"
            >{{ pt.label }}</text>
          </svg>
        </div>
      </div>
    </template>

    <!-- Add Keyword Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-card">
        <h3 class="card-title" style="margin-bottom:16px">Track New Keyword</h3>
        <div style="margin-bottom:12px">
          <label class="form-label">Keyword</label>
          <input v-model="newKw.keyword" class="form-input" placeholder="e.g. growth hacking tools" />
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Target URL (optional)</label>
          <input v-model="newKw.target_url" class="form-input" placeholder="https://..." />
        </div>
        <div class="flex gap-8" style="justify-content:flex-end">
          <button class="btn btn-secondary" @click="showAddModal = false">Cancel</button>
          <button class="btn btn-primary" @click="addKeyword" :disabled="!newKw.keyword.trim() || adding">{{ adding ? 'Adding...' : 'Track Keyword' }}</button>
        </div>
        <p v-if="addError" class="text-sm" style="color:var(--color-danger);margin-top:12px">{{ addError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const loading = ref(true)
const keywords = ref([])
const expandedKw = ref(null)
const showAddModal = ref(false)
const adding = ref(false)
const addError = ref('')
const newKw = ref({ keyword: '', target_url: '' })

const chartW = 700
const chartH = 200
const chartPadLeft = 50
const chartPadTop = 15
const chartPadBottom = 25

const avgPosition = computed(() => {
  const ranked = keywords.value.filter(k => k.current_rank)
  if (!ranked.length) return '--'
  return Math.round(ranked.reduce((s, k) => s + k.current_rank, 0) / ranked.length)
})

const improved = computed(() => keywords.value.filter(k => k.rank_change > 0).length)
const declined = computed(() => keywords.value.filter(k => k.rank_change < 0).length)

const yLabels = computed(() => {
  if (!expandedKw.value?._history?.length) return [1, 10, 20, 30]
  const ranks = expandedKw.value._history.map(h => h.rank).filter(Boolean)
  const min = Math.max(1, Math.min(...ranks) - 2)
  const max = Math.max(...ranks) + 2
  const step = Math.max(1, Math.round((max - min) / 4))
  const labels = []
  for (let r = min; r <= max; r += step) labels.push(r)
  return labels
})

function rankToY(rank) {
  const ranks = expandedKw.value?._history?.map(h => h.rank).filter(Boolean) || [1, 50]
  const min = Math.max(1, Math.min(...ranks) - 2)
  const max = Math.max(...ranks) + 2
  const usableH = chartH - chartPadTop - chartPadBottom
  // Lower rank = higher on chart (inverted)
  return chartPadTop + ((rank - min) / (max - min)) * usableH
}

const chartPoints = computed(() => {
  if (!expandedKw.value?._history?.length) return []
  const history = expandedKw.value._history
  const usableW = chartW - chartPadLeft - 20
  return history.map((h, i) => ({
    x: chartPadLeft + (i / Math.max(history.length - 1, 1)) * usableW,
    y: rankToY(h.rank),
    label: new Date(h.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }))
})

const chartLine = computed(() => chartPoints.value.map(p => `${p.x},${p.y}`).join(' '))

const areaPath = computed(() => {
  const pts = chartPoints.value
  if (!pts.length) return ''
  const bottom = chartH - chartPadBottom
  let d = `M ${pts[0].x} ${bottom}`
  pts.forEach(p => { d += ` L ${p.x} ${p.y}` })
  d += ` L ${pts[pts.length - 1].x} ${bottom} Z`
  return d
})

function cleanUrl(url) {
  if (!url) return ''
  try { return new URL(url).pathname } catch { return url }
}

function rankClass(rank) {
  if (!rank) return ''
  if (rank <= 3) return 'rank-top3'
  if (rank <= 10) return 'rank-top10'
  if (rank <= 20) return 'rank-top20'
  return 'rank-low'
}

function diffClass(d) {
  if (d < 30) return 'diff-easy'
  if (d < 60) return 'diff-medium'
  return 'diff-hard'
}

function sparklinePoints(history) {
  if (!history?.length) return ''
  const ranks = history.map(h => h.rank).filter(Boolean)
  if (!ranks.length) return ''
  const min = Math.min(...ranks) - 1
  const max = Math.max(...ranks) + 1
  const range = max - min || 1
  return ranks.map((r, i) => {
    const x = (i / Math.max(ranks.length - 1, 1)) * 96 + 2
    const y = 2 + ((r - min) / range) * 24
    return `${x},${y}`
  }).join(' ')
}

async function toggleHistory(kw) {
  if (expandedKw.value?.id === kw.id) {
    expandedKw.value = null
    return
  }
  if (!kw._history) {
    try {
      const { data } = await analyticsApi.keywordHistory(props.websiteId, kw.id)
      const d = data?.data || data
      kw._history = d.history || []
    } catch (e) {
      console.error('History fetch error', e)
      kw._history = []
    }
  }
  expandedKw.value = kw
}

async function addKeyword() {
  adding.value = true
  addError.value = ''
  try {
    const { data } = await analyticsApi.addKeyword(props.websiteId, newKw.value)
    const kw = data?.data || data
    keywords.value.unshift({ ...kw, rank_change: null })
    newKw.value = { keyword: '', target_url: '' }
    showAddModal.value = false
  } catch (e) {
    addError.value = e.response?.data?.error || 'Failed to add keyword.'
  } finally {
    adding.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await analyticsApi.keywords(props.websiteId)
    keywords.value = (data?.data || data || []).map(k => ({ ...k, _history: null }))
  } catch (e) {
    console.error('Keywords fetch error', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

.kw-stats { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-pill {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg);
  padding: 14px 20px; display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 120px;
}
.stat-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); }

.kw-row { cursor: pointer; transition: background 0.15s; }
.kw-row:hover { background: var(--bg-surface); }
.kw-name { font-weight: 600; color: var(--text-primary); }
.kw-url { font-size: var(--font-xs); color: var(--text-muted); margin-top: 2px; }

.rank-badge {
  display: inline-block; min-width: 32px; padding: 4px 10px; border-radius: var(--radius-full);
  font-weight: 700; font-size: var(--font-sm); text-align: center;
}
.rank-top3 { background: rgba(34,197,94,0.15); color: var(--color-success); }
.rank-top10 { background: rgba(59,130,246,0.12); color: #3b82f6; }
.rank-top20 { background: rgba(234,179,8,0.12); color: #ca8a04; }
.rank-low { background: rgba(239,68,68,0.1); color: var(--color-danger); }

.change-up { color: var(--color-success); font-weight: 700; }
.change-down { color: var(--color-danger); font-weight: 700; }
.change-flat { color: var(--text-muted); }

.diff-bar-wrap { display: flex; align-items: center; gap: 8px; }
.diff-bar { height: 5px; border-radius: var(--radius-full); min-width: 2px; }
.diff-easy { background: var(--color-success); }
.diff-medium { background: #eab308; }
.diff-hard { background: var(--color-danger); }
.diff-num { font-size: var(--font-xs); color: var(--text-muted); min-width: 20px; }

.sparkline { cursor: pointer; }

/* Rank Chart */
.rank-chart-wrap { overflow-x: auto; }
.rank-chart { width: 100%; min-height: 200px; display: block; }
.chart-area { fill: var(--brand-accent); opacity: 0.08; }
.chart-label { fill: var(--text-muted); font-size: 10px; }
.grid-line { stroke: var(--border-color); stroke-width: 0.5; opacity: 0.4; }
.chart-dot { transition: r 0.2s; }
.chart-dot:hover { r: 5; }

/* Modal (reuses AppLayout modal styles but scoped fallback) */
.modal-overlay {
  position: fixed; inset: 0; z-index: 200; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
}
.modal-card {
  background: var(--bg-card); border-radius: var(--radius-lg); padding: 28px;
  width: 440px; max-width: 90vw; box-shadow: var(--shadow-lg);
}
.form-label { display: block; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }

@media (max-width: 768px) {
  .kw-stats { flex-direction: column; }
}
</style>
