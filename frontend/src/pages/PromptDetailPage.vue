<template>
  <div class="pd-page fade-in">
    <!-- Breadcrumb chip -->
    <div class="pd-breadcrumb">
      <router-link :to="`/llm-ranking/${websiteId}/prompts`" class="pd-bc-link">
        <ChevronLeft :size="14" :stroke-width="2" />
        Prompts
      </router-link>
      <span class="pd-bc-sep">/</span>
      <span class="pd-bc-current">{{ promptTextShort }}</span>
    </div>

    <!-- Header -->
    <header class="pd-header">
      <div class="pd-header-eyebrow">
        <Sparkles :size="12" :stroke-width="2" />
        <span>Prompt</span>
      </div>
      <h1 class="pd-title">{{ promptText || 'Loading…' }}</h1>
    </header>

    <!-- Metadata strip -->
    <div class="pd-meta-grid">
      <div class="pd-meta">
        <div class="pd-meta-label"><Clock :size="12" :stroke-width="2"/>Date added</div>
        <div class="pd-meta-val">{{ relativeTime(detail?.prompt?.created_at) }}</div>
      </div>
      <div class="pd-meta">
        <div class="pd-meta-label"><Tag :size="12" :stroke-width="2"/>Topic</div>
        <div class="pd-meta-val">{{ detail?.prompt?.topic || '—' }}</div>
      </div>
      <div class="pd-meta">
        <div class="pd-meta-label"><Activity :size="12" :stroke-width="2"/>Demand</div>
        <div class="pd-meta-val pd-meta-bars">
          <span v-for="i in 4" :key="i" class="pd-bar" :class="{ 'is-on': demandLevel >= i }"></span>
        </div>
      </div>
      <div class="pd-meta">
        <div class="pd-meta-label"><Repeat :size="12" :stroke-width="2"/>Runs</div>
        <div class="pd-meta-val">{{ detail?.prompt?.runs_count || 0 }}</div>
      </div>
      <div class="pd-meta">
        <div class="pd-meta-label"><CircleDot :size="12" :stroke-width="2"/>Status</div>
        <div class="pd-meta-val">
          <span class="pd-status" :class="`is-${detail?.status || 'inactive'}`">
            <span class="pd-status-dot"></span>
            {{ detail?.status === 'active' ? 'Active' : 'Inactive' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Overview: Visibility chart + Top brands table -->
    <section class="pd-overview-head">
      <h2 class="pd-section-title">
        <BarChart3 :size="16" :stroke-width="2"/>
        Overview
      </h2>
      <p class="pd-section-sub">How often each brand appears in AI-generated discussions of this prompt.</p>
    </section>

    <div class="pd-grid pd-grid-2">
      <div class="pd-card">
        <div class="pd-card-head">
          <h3>
            <ChartLine :size="14" :stroke-width="2"/>
            Visibility
          </h3>
          <span class="pd-card-meta">
            Across {{ detail?.total_responses || 0 }} model responses
          </span>
        </div>
        <div class="pd-chart">
          <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
          <div v-else class="pd-empty-inline">
            <Inbox :size="32" :stroke-width="1.5"/>
            <p>No model responses yet for this prompt.</p>
          </div>
        </div>
      </div>

      <div class="pd-card">
        <div class="pd-card-head">
          <h3>
            <Trophy :size="14" :stroke-width="2"/>
            Top {{ Math.min(7, topBrands.length || 0) }} brands
          </h3>
        </div>
        <div class="pd-table-wrap">
          <table class="pd-table">
            <thead>
              <tr>
                <th class="num">#</th>
                <th>Brand</th>
                <th class="num">Visibility</th>
                <th class="num">SOV</th>
                <th class="num">Sentiment</th>
                <th class="num">Position</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(b, i) in topBrands" :key="b.name" :class="{ 'is-self': b.is_self }">
                <td class="num">{{ i + 1 }}</td>
                <td>
                  <span class="pd-brand-name">{{ b.name }}</span>
                  <span v-if="b.is_self" class="pd-self-pill">you</span>
                </td>
                <td class="num">{{ b.visibility_pct }}%</td>
                <td class="num">{{ b.sov_pct }}%</td>
                <td class="num">
                  <span v-if="b.sentiment_score != null" class="pd-sent">
                    <span class="pd-sent-dot" :class="sentimentClass(b.sentiment_score)"></span>
                    {{ b.sentiment_score }}
                  </span>
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="num">
                  <span v-if="b.avg_position != null">#{{ b.avg_position }}</span>
                  <span v-else class="text-muted">—</span>
                </td>
              </tr>
              <tr v-if="!topBrands.length">
                <td colspan="6" class="pd-table-empty">No brand mentions yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Top Domains + Domain type breakdown -->
    <section class="pd-overview-head" style="margin-top: 28px">
      <h2 class="pd-section-title">
        <Globe :size="16" :stroke-width="2"/>
        Top domains
      </h2>
      <p class="pd-section-sub">Domains AI models retrieved when answering this prompt.</p>
    </section>

    <div class="pd-grid pd-grid-2">
      <div class="pd-card">
        <div class="pd-card-head">
          <h3>
            <Link2 :size="14" :stroke-width="2"/>
            By citation count
          </h3>
        </div>
        <div class="pd-table-wrap">
          <table class="pd-table">
            <thead>
              <tr>
                <th class="num">#</th>
                <th>Domain</th>
                <th class="num">Retrieved</th>
                <th class="num">Citation rate</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(d, i) in topDomains" :key="d.apex_domain">
                <td class="num">{{ i + 1 }}</td>
                <td>
                  <img :src="faviconFor(d.apex_domain)" :alt="d.domain" class="pd-favicon" @error="onFaviconError($event, d)"/>
                  <a :href="`https://${d.apex_domain}`" target="_blank" rel="noopener">{{ d.apex_domain }}</a>
                </td>
                <td class="num">{{ d.retrieved_pct }}%</td>
                <td class="num">{{ d.citation_rate.toFixed(1) }}</td>
                <td>
                  <span class="pd-type-pill" :class="`is-${(d.source_class || 'other').toLowerCase()}`">
                    {{ typeLabel(d.source_class) }}
                  </span>
                </td>
              </tr>
              <tr v-if="!topDomains.length">
                <td colspan="5" class="pd-table-empty">No citations yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="pd-card">
        <div class="pd-card-head">
          <h3>
            <PieChart :size="14" :stroke-width="2"/>
            Domain types
          </h3>
          <span class="pd-card-meta">{{ detail?.total_retrievals || 0 }} retrievals</span>
        </div>
        <ul class="pd-types">
          <li v-for="t in domainTypes" :key="t.key">
            <span class="pd-type-dot" :class="`is-${(t.key || 'other').toLowerCase()}`"></span>
            <span class="pd-type-name">{{ typeLabel(t.key) }}</span>
            <span class="pd-type-pct">{{ t.pct }}%</span>
          </li>
          <li v-if="!domainTypes.length" class="pd-empty-inline" style="padding: 12px">
            No retrievals yet.
          </li>
        </ul>
      </div>
    </div>

    <div v-if="loading && !detail" class="pd-loading">Loading prompt analytics…</div>
    <div v-if="error" class="pd-error">{{ error }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, Tooltip, Legend,
} from 'chart.js'
import {
  Activity, BarChart3, ChartLine, ChevronLeft, CircleDot, Clock,
  Globe, Inbox, Link2, PieChart, Repeat, Sparkles, Tag, Trophy,
} from '@lucide/vue'
import promptLibrary from '@/api/promptLibrary'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const route = useRoute()
const websiteId = route.params.websiteId
const promptId = route.params.promptId

const detail = ref(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await promptLibrary.promptDetailAgg(websiteId, promptId)
    detail.value = data?.data || data || null
  } catch (e) {
    error.value = e?.displayMessage || 'Could not load prompt analytics.'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const promptText = computed(() => detail.value?.prompt?.text || '')
const promptTextShort = computed(() => {
  const t = promptText.value
  return t.length > 60 ? t.slice(0, 60) + '…' : t
})
const demandLevel = computed(() => {
  const score = Number(detail.value?.prompt?.demand_score) || 0
  if (score >= 0.75) return 4
  if (score >= 0.5)  return 3
  if (score >= 0.25) return 2
  if (score > 0)     return 1
  return 0
})

const topBrands = computed(() => (detail.value?.brands || []).slice(0, 7))
const topDomains = computed(() => detail.value?.top_domains || [])
const domainTypes = computed(() => detail.value?.domain_types || [])

const TYPE_LABELS = {
  your_site: 'Your site',
  competitor: 'Competitor',
  ugc: 'UGC',
  corporate: 'Corporate',
  reference: 'Reference',
  editorial: 'Editorial',
  institutional: 'Institutional',
  other: 'Other',
}
function typeLabel(key) { return TYPE_LABELS[(key || 'other').toLowerCase()] || key }

function sentimentClass(score) {
  if (score == null) return 'is-mute'
  if (score >= 70) return 'is-pos'
  if (score >= 50) return 'is-neu'
  return 'is-neg'
}

const BRAND_COLORS = [
  '#10b981', '#374151', '#f59e0b', '#ec4899', '#a3e635', '#06b6d4', '#6366f1', '#94a3b8',
]
const chartData = computed(() => {
  const b = topBrands.value
  if (!b.length) return null
  return {
    labels: b.map((x) => x.name),
    datasets: [{
      label: 'Visibility %',
      data: b.map((x) => x.visibility_pct),
      backgroundColor: b.map((_, i) => BRAND_COLORS[i % BRAND_COLORS.length]),
      borderRadius: 8,
      barThickness: 28,
    }],
  }
})
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y}% visibility` } },
  },
  scales: {
    y: { min: 0, max: 100, ticks: { callback: (v) => v + '%' }, grid: { color: 'rgba(0,0,0,0.05)' } },
    x: { grid: { display: false } },
  },
}

function faviconFor(domain) {
  if (!domain) return ''
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=32`
}
function onFaviconError(ev, d) {
  const letter = (d.apex_domain || d.domain || '?').charAt(0).toUpperCase()
  ev.target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20'%3E%3Crect width='20' height='20' rx='5' fill='%23e5e7eb'/%3E%3Ctext x='10' y='14' text-anchor='middle' font-size='10' font-family='sans-serif' fill='%236b7280' font-weight='600'%3E${letter}%3C/text%3E%3C/svg%3E`
}

function relativeTime(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} hr ago`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d}d ago`
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<style scoped>
.pd-page { padding: 32px 40px 56px; color: var(--text-primary); }

.pd-breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 8px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 999px;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 24px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.pd-bc-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
}
.pd-bc-link:hover { color: var(--text-primary); }
.pd-bc-sep { color: var(--border-color); }
.pd-bc-current { color: var(--text-primary); font-weight: 500; }

.pd-header { margin-bottom: 28px; }
.pd-header-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  background: rgba(255, 107, 53, 0.10);
  color: var(--brand-accent, #ff6b35);
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
}
.pd-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--text-primary);
  line-height: 1.15;
  max-width: 56rem;
}

.pd-meta-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  padding: 18px 22px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 14px;
  margin-bottom: 28px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
@media (max-width: 900px) { .pd-meta-grid { grid-template-columns: repeat(2, 1fr); row-gap: 18px; padding: 16px; } }
.pd-meta { padding: 0 18px; border-left: 1px solid var(--border-color, #e5e7eb); }
.pd-meta:first-child { border-left: none; padding-left: 0; }
.pd-meta-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-weight: 600;
}
.pd-meta-label svg { color: var(--text-muted); }
.pd-meta-val { font-size: 14px; color: var(--text-primary); font-weight: 500; line-height: 1.3; }
.pd-meta-bars { display: inline-flex; gap: 3px; }
.pd-bar { width: 5px; height: 14px; border-radius: 2px; background: var(--border-color, #e5e7eb); }
.pd-bar.is-on { background: #10b981; }
.pd-status {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px 3px 8px;
  border-radius: 999px;
  font-size: 12px; font-weight: 600;
}
.pd-status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pd-status.is-active { background: rgba(16,185,129,0.12); color: #047857; }
.pd-status.is-inactive { background: var(--bg-subtle, #fafafa); color: var(--text-muted); }

.pd-overview-head { margin-bottom: 14px; }
.pd-section-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 4px;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.015em;
}
.pd-section-title svg { color: var(--text-muted); }
.pd-section-sub { margin: 0; font-size: 0.86rem; color: var(--text-secondary); }

.pd-grid { display: grid; gap: 18px; }
.pd-grid-2 { grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); }
@media (max-width: 960px) { .pd-grid-2 { grid-template-columns: 1fr; } }

.pd-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 14px;
  padding: 20px 22px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
}
.pd-card:hover {
  box-shadow: 0 4px 16px -8px rgba(15, 23, 42, 0.12), 0 1px 2px rgba(15, 23, 42, 0.04);
  border-color: var(--border-hover, #d4d4d8);
}
.pd-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 14px;
}
.pd-card-head h3 {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}
.pd-card-head h3 svg { color: var(--text-muted); }
.pd-card-meta {
  font-size: 0.78rem;
  color: var(--text-muted);
  background: var(--bg-subtle, #fafafa);
  padding: 3px 10px;
  border-radius: 999px;
}

.pd-chart { height: 280px; position: relative; }
.pd-empty-inline {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 200px;
  color: var(--text-muted);
  font-size: 0.88rem;
}
.pd-empty-inline svg { color: var(--text-muted); opacity: 0.55; }
.pd-empty-inline p { margin: 0; }

.pd-table-wrap { overflow-x: auto; }
.pd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.pd-table th {
  text-align: left;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.pd-table th.num, .pd-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.pd-table td {
  padding: 10px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.pd-table tbody tr:last-child td { border-bottom: none; }
.pd-table tbody tr:hover { background: var(--bg-subtle, #fafafa); }
.pd-table tr.is-self td:nth-child(2) { font-weight: 600; }
.pd-table-empty { text-align: center; color: var(--text-muted); padding: 18px; }

.pd-favicon {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  vertical-align: -5px;
  margin-right: 8px;
  background: var(--bg-subtle, #fafafa);
}
.pd-table a { color: var(--text-primary); text-decoration: none; border-bottom: 1px solid transparent; }
.pd-table a:hover { border-bottom-color: var(--text-muted); }

.pd-brand-name { font-weight: 500; }
.pd-self-pill {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 7px;
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-radius: 999px;
  background: var(--brand-accent, #ff6b35);
  color: #fff;
}

.pd-sent { display: inline-flex; align-items: center; gap: 6px; }
.pd-sent-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.pd-sent-dot.is-pos { background: #10b981; }
.pd-sent-dot.is-neu { background: #6b7280; }
.pd-sent-dot.is-neg { background: #ef4444; }
.pd-sent-dot.is-mute { background: var(--border-color); }

.pd-type-pill {
  display: inline-flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 999px;
}
.pd-type-pill.is-corporate { background: rgba(245,158,11,0.14); color: #b45309; }
.pd-type-pill.is-ugc { background: rgba(99,102,241,0.14); color: #4338ca; }
.pd-type-pill.is-reference { background: rgba(139,92,246,0.14); color: #6d28d9; }
.pd-type-pill.is-editorial { background: rgba(16,185,129,0.14); color: #047857; }
.pd-type-pill.is-institutional { background: rgba(6,182,212,0.14); color: #0e7490; }
.pd-type-pill.is-your_site { background: rgba(255,107,53,0.14); color: #c2410c; }
.pd-type-pill.is-competitor { background: rgba(239,68,68,0.14); color: #b91c1c; }
.pd-type-pill.is-other { background: var(--bg-subtle, #fafafa); color: var(--text-muted); }

.pd-types { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.pd-types li {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  font-size: 0.88rem;
}
.pd-types li:last-child { border-bottom: none; }
.pd-type-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.pd-type-dot.is-corporate { background: #f59e0b; }
.pd-type-dot.is-ugc { background: #6366f1; }
.pd-type-dot.is-reference { background: #8b5cf6; }
.pd-type-dot.is-editorial { background: #10b981; }
.pd-type-dot.is-institutional { background: #06b6d4; }
.pd-type-dot.is-your_site { background: #ff6b35; }
.pd-type-dot.is-competitor { background: #ef4444; }
.pd-type-dot.is-other { background: #94a3b8; }
.pd-type-name { color: var(--text-primary); }
.pd-type-pct { font-variant-numeric: tabular-nums; color: var(--text-muted); }

.pd-loading { padding: 40px 0; text-align: center; color: var(--text-muted); }
.pd-error { padding: 20px; text-align: center; color: #b91c1c; }
.text-muted { color: var(--text-muted); }

[data-theme="dark"] .pd-card,
[data-theme="dark"] .pd-meta-grid { background: var(--bg-card); border-color: var(--border-color); }
[data-theme="dark"] .pd-table th,
[data-theme="dark"] .pd-table td { border-color: var(--border-color); color: var(--text-primary); }
[data-theme="dark"] .pd-table th { color: var(--text-muted); }
[data-theme="dark"] .pd-table tbody tr:hover { background: var(--bg-card-hover); }
[data-theme="dark"] .pd-favicon { background: var(--bg-card-hover); }
</style>
