<template>
  <div class="analytics-page fade-in">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Analytics</h1>
        <p class="page-subtitle">Product analytics, funnels, retention, and AI insights.</p>
      </div>
      <div class="flex gap-8 items-center">
        <div class="period-tabs">
          <button v-for="p in periods" :key="p.value" class="period-tab" :class="{ active: period === p.value }" @click="changePeriod(p.value)">{{ p.label }}</button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="analytics-tabs">
      <button v-for="tab in tabs" :key="tab.id" class="atab" :class="{ active: activeTab === tab.id }" @click="switchTab(tab.id)">
        <svg class="atab-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" v-html="tab.svg"></svg>
        <span class="atab-label">{{ tab.label }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span style="margin-top:12px">Loading analytics...</span>
    </div>
    <div v-if="refreshing && !loading" class="refresh-indicator">
      <div class="refresh-dot"></div> Updating...
    </div>

    <template v-else>
      <!-- Empty State -->
      <div v-if="noData && activeTab === 'overview'" class="empty-state-card">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--brand-accent)" stroke-width="1.5">
            <rect x="6" y="6" width="36" height="36" rx="4"/>
            <path d="M6 18h36M18 18v24"/>
            <circle cx="30" cy="30" r="6" fill="none" stroke-dasharray="4"/>
          </svg>
        </div>
        <h3 class="empty-title">Install the tracking pixel</h3>
        <p class="empty-desc">Add the FetchBot tracking snippet to your website to start collecting real visitor data.</p>
        <div class="empty-snippet">
          <code>&lt;script src="/fetchbot-pixel.js" data-site="YOUR_PIXEL_KEY" async&gt;&lt;/script&gt;</code>
        </div>
        <p class="empty-hint">Go to <strong>Projects → Settings</strong> to copy your personalized snippet.</p>
      </div>

      <!-- ═══════════ TAB 1: Overview ═══════════ -->
      <div v-show="activeTab === 'overview' && !noData">
        <!-- KPI Cards -->
        <div class="kpi-grid">
          <div class="kpi-card" v-for="stat in stats" :key="stat.label" :class="stat.highlight ? 'kpi-highlight' : ''">
            <div class="kpi-header">
              <span class="kpi-label">{{ stat.label }}</span>
              <span class="kpi-trend" :class="stat.trend >= 0 ? 'trend-up' : 'trend-down'">
                {{ stat.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(stat.trend) }}%
              </span>
            </div>
            <div class="kpi-value">{{ stat.value }}</div>
          </div>
        </div>

        <!-- Traffic Chart (Chart.js) -->
        <div class="card chart-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Traffic Overview</h3>
              <p class="card-subtitle">Visitor sessions over time</p>
            </div>
          </div>
          <div class="chart-container" style="height:280px;position:relative">
            <Line v-if="chartData.length" :data="trafficChartData" :options="trafficChartOptions" />
            <div v-else class="empty-inline">No chart data yet</div>
          </div>
        </div>

        <!-- Sources + Pages Row -->
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Sources</h3></div>
            <div class="chart-container" style="height:220px;position:relative" v-if="sources.length">
              <Bar :data="sourcesChartData" :options="sourcesChartOptions" />
            </div>
            <div v-else class="empty-inline">No source data yet</div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Pages</h3></div>
            <table class="data-table">
              <thead><tr><th>Page</th><th style="text-align:right">Views</th></tr></thead>
              <tbody>
                <tr v-for="(page, i) in topPages" :key="i">
                  <td><span class="page-rank">{{ i + 1 }}</span> {{ page.url }}</td>
                  <td style="text-align:right" class="font-semibold">{{ page.views }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!topPages.length" class="empty-inline">No page data yet</div>
          </div>
        </div>

        <!-- Devices + Countries Row -->
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Devices</h3></div>
            <div class="chart-container" style="height:200px;position:relative" v-if="devices.length">
              <Doughnut :data="devicesChartData" :options="devicesChartOptions" />
            </div>
            <div v-else class="empty-inline">No device data yet</div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Countries</h3></div>
            <div class="country-list" v-if="countries.length">
              <div v-for="(c, i) in countries" :key="i" class="country-item">
                <div class="country-rank">{{ i + 1 }}</div>
                <div class="country-info">
                  <span class="country-name">{{ c.name }}</span>
                  <div class="country-bar-wrap"><div class="country-bar" :style="{ width: c.pct + '%' }"></div></div>
                </div>
                <span class="font-semibold">{{ c.visitors }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">No geo data yet</div>
          </div>
        </div>

        <!-- Realtime -->
        <div class="card realtime-card" v-if="realtimeVisitors > 0">
          <div class="realtime-dot"></div>
          <span class="font-semibold">{{ realtimeVisitors }} active users</span>
          <span class="text-muted text-sm"> right now</span>
        </div>
      </div>

      <!-- ═══════════ TAB 2: Funnels ═══════════ -->
      <div v-show="activeTab === 'funnels'">
        <div class="card" style="margin-bottom:20px">
          <div class="card-header">
            <h3 class="card-title">Conversion Funnels</h3>
            <button class="btn btn-primary btn-sm" @click="showCreateFunnel = true">+ New Funnel</button>
          </div>
          <!-- Saved funnels -->
          <div v-if="funnelList.length" class="funnel-list">
            <div v-for="f in funnelList" :key="f.id" class="funnel-item" @click="runFunnel(f.id)">
              <span class="font-semibold">{{ f.name }}</span>
              <span class="text-xs text-muted">{{ f.steps?.length || 0 }} steps</span>
            </div>
          </div>
          <div v-else class="empty-inline">No funnels yet. Create one to track conversions.</div>
        </div>

        <!-- Funnel result -->
        <div v-if="funnelResult" class="card">
          <div class="card-header">
            <h3 class="card-title">{{ funnelResult.name }}</h3>
            <span class="badge badge-success">{{ funnelResult.overall_conversion_pct }}% conversion</span>
          </div>
          <div class="funnel-viz">
            <div v-for="(step, i) in funnelResult.steps" :key="i" class="funnel-step">
              <div class="funnel-bar" :style="{ height: step.conversion_pct + '%' }">
                <div class="funnel-bar-fill"></div>
              </div>
              <div class="funnel-step-info">
                <div class="font-semibold text-sm">{{ step.name }}</div>
                <div class="text-xs text-muted">{{ step.visitors }} visitors</div>
                <div v-if="step.drop_off_pct > 0" class="text-xs text-danger">-{{ step.drop_off_pct }}% drop</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Create Funnel Modal -->
        <div v-if="showCreateFunnel" class="modal-overlay" @click.self="showCreateFunnel = false">
          <div class="modal-card" style="max-width:500px">
            <h3 class="card-title" style="margin-bottom:16px">Create Funnel</h3>
            <div class="form-group"><label class="form-label">Name</label><input v-model="newFunnel.name" class="form-input" placeholder="e.g. Signup Flow" /></div>
            <div v-for="(step, i) in newFunnel.steps" :key="i" class="form-group" style="display:flex;gap:8px">
              <input v-model="step.name" class="form-input" :placeholder="'Step ' + (i+1) + ' name'" style="flex:1" />
              <input v-model="step.value" class="form-input" :placeholder="'URL contains...'" style="flex:1" />
            </div>
            <button class="btn btn-secondary btn-sm" @click="newFunnel.steps.push({name:'',type:'url',value:''})" style="margin-bottom:16px">+ Add Step</button>
            <div class="flex gap-8">
              <button class="btn btn-primary" @click="createFunnel">Create</button>
              <button class="btn btn-secondary" @click="showCreateFunnel = false">Cancel</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 3: Retention ═══════════ -->
      <div v-show="activeTab === 'retention'">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Cohort Retention</h3>
            <p class="card-subtitle">How many visitors return over time</p>
          </div>
          <div v-if="retentionData.rows && retentionData.rows.length" class="retention-matrix">
            <table class="data-table retention-table">
              <thead>
                <tr>
                  <th>Cohort</th>
                  <th>Size</th>
                  <th v-for="w in maxRetentionWeeks" :key="w">Wk {{ w - 1 }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in retentionData.rows" :key="row.cohort">
                  <td class="font-semibold">{{ row.cohort }}</td>
                  <td>{{ row.cohort_size }}</td>
                  <td v-for="(w, i) in row.weeks" :key="i" :style="{ background: retentionColor(w.pct) }" class="retention-cell">
                    {{ w.pct }}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-inline">No retention data yet. Data appears after visitors return to your site.</div>
        </div>
      </div>

      <!-- ═══════════ TAB 4: Flows ═══════════ -->
      <div v-show="activeTab === 'flows'">
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Page Flows</h3></div>
            <div v-if="flowData.links && flowData.links.length" class="flow-list">
              <div v-for="(link, i) in flowData.links.slice(0, 15)" :key="i" class="flow-item">
                <span class="flow-page">{{ link.source }}</span>
                <span class="flow-arrow">→</span>
                <span class="flow-page">{{ link.target }}</span>
                <span class="flow-count">{{ link.value }}×</span>
              </div>
            </div>
            <div v-else class="empty-inline">No flow data yet</div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">Entry & Exit Pages</h3></div>
            <div v-if="entryExitData.entry_pages && entryExitData.entry_pages.length">
              <h4 class="text-sm font-semibold" style="margin-bottom:8px;color:var(--color-success)">↓ Entry Pages</h4>
              <div v-for="p in entryExitData.entry_pages" :key="'e'+p.page" class="flow-stat-item">
                <span class="truncate" style="max-width:200px">{{ p.page }}</span>
                <span class="font-semibold">{{ p.count }}</span>
              </div>
              <h4 class="text-sm font-semibold" style="margin:16px 0 8px;color:var(--color-danger)">↑ Exit Pages</h4>
              <div v-for="p in entryExitData.exit_pages || []" :key="'x'+p.page" class="flow-stat-item">
                <span class="truncate" style="max-width:200px">{{ p.page }}</span>
                <span class="font-semibold">{{ p.count }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">No entry/exit data yet</div>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 5: AI Insights ═══════════ -->
      <div v-show="activeTab === 'insights'">
        <div class="insights-grid">
          <div v-for="(insight, i) in insightsData.insights || []" :key="i" class="insight-card" :class="'insight-' + insight.type">
            <div class="insight-header">
              <svg class="insight-type-icon" width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 10v1"/></svg>
              <span class="insight-badge" :class="'ibadge-' + insight.type">{{ insight.type }}</span>
              <span v-if="insight.metric" class="insight-metric">{{ insight.metric }}</span>
            </div>
            <h4 class="insight-title">{{ insight.title }}</h4>
            <p class="insight-desc">{{ insight.description }}</p>
            <div class="insight-action" v-if="insight.action">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 7h12M8 2l5 5-5 5"/></svg>
              {{ insight.action }}
            </div>
          </div>
        </div>
        <div v-if="!insightsData.insights || !insightsData.insights.length" class="empty-state-card">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5" style="margin-bottom:16px"><circle cx="24" cy="24" r="16"/><path d="M18 28c2-4 4-8 6-8s4 4 6 8"/><circle cx="24" cy="18" r="3"/></svg>
          <h3 class="empty-title">AI Insights need more data</h3>
          <p class="empty-desc">Once you have enough traffic data, FetchBot AI will detect anomalies, spot trends, and suggest actionable improvements.</p>
        </div>

        <!-- Suggested Actions -->
        <div v-if="insightsData.actions && insightsData.actions.length" class="card" style="margin-top:20px">
          <div class="card-header"><h3 class="card-title">Suggested Actions</h3></div>
          <div v-for="(a, i) in insightsData.actions" :key="i" class="action-item">
            <span class="action-priority" :class="'ap-' + a.priority">{{ a.priority }}</span>
            <div>
              <div class="font-semibold text-sm">{{ a.action }}</div>
              <div class="text-xs text-muted">{{ a.reason }}</div>
            </div>
            <span v-if="a.impact" class="text-sm font-semibold">{{ a.impact }}</span>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 6: Visitors ═══════════ -->
      <div v-show="activeTab === 'visitors'">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Visitor Profiles</h3>
            <span class="text-xs text-muted">{{ visitorList.length }} visitors</span>
          </div>
          <table class="data-table" v-if="visitorList.length">
            <thead>
              <tr><th>Visitor</th><th>Device</th><th>Country</th><th>Visits</th><th>Events</th><th>Last Seen</th></tr>
            </thead>
            <tbody>
              <tr v-for="v in visitorList" :key="v.id" class="clickable-row" @click="loadTimeline(v.id)">
                <td>
                  <div class="visitor-id">{{ v.fingerprint_hash?.substring(0, 8) }}...</div>
                  <div class="text-xs text-muted" v-if="v.company_name">{{ v.company_name }}</div>
                </td>
                <td>{{ v.device_type || '--' }}<br><span class="text-xs text-muted">{{ v.browser }}</span></td>
                <td>{{ v.geo_country || '--' }} {{ v.geo_city || '' }}</td>
                <td class="font-semibold">{{ v.visit_count }}</td>
                <td>{{ v.event_count }}</td>
                <td class="text-xs text-muted">{{ formatDate(v.last_seen) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-inline">No visitor data yet</div>
        </div>

        <!-- Visitor Timeline -->
        <div v-if="timelineEvents.length" class="card" style="margin-top:20px">
          <div class="card-header">
            <h3 class="card-title">Event Timeline</h3>
            <button class="btn btn-secondary btn-sm" @click="timelineEvents = []">Close</button>
          </div>
          <div class="timeline">
            <div v-for="e in timelineEvents" :key="e.id" class="timeline-item">
              <div class="timeline-dot" :class="'dot-' + e.event_type"></div>
              <div class="timeline-content">
                <span class="badge badge-sm" :class="eventBadge(e.event_type)">{{ e.event_type }}</span>
                <span class="text-sm truncate" style="max-width:300px">{{ e.url }}</span>
                <span class="text-xs text-muted">{{ formatTime(e.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAnalyticsStore } from '@/stores/analytics'
import { Line, Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement,
  Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement,
  Filler, Tooltip, Legend,
)

// Global Chart.js defaults for dark/professional look
ChartJS.defaults.color = '#8a8a9a'
ChartJS.defaults.font.family = "'Inter', 'SF Pro Display', system-ui, sans-serif"
ChartJS.defaults.font.size = 11

const route = useRoute()
const store = useAnalyticsStore()
const websiteId = route.params.websiteId

const tabs = [
  { id: 'overview', svg: '<path d="M2 14V6l4-4 4 4 4-4v12" stroke-linejoin="round"/>', label: 'Overview' },
  { id: 'funnels', svg: '<path d="M2 2h12l-3 5v5l-2 2V7z"/>', label: 'Funnels' },
  { id: 'retention', svg: '<path d="M1 8a7 7 0 0114 0M12 5l3 3-3 3"/><circle cx="8" cy="8" r="2"/>', label: 'Retention' },
  { id: 'flows', svg: '<path d="M1 4h4l3 4-3 4H1M15 4h-4l-3 4 3 4h4"/>', label: 'Flows' },
  { id: 'insights', svg: '<circle cx="8" cy="6" r="4"/><path d="M5 10v1a3 3 0 006 0v-1"/><line x1="8" y1="14" x2="8" y2="15"/>', label: 'AI Insights' },
  { id: 'visitors', svg: '<circle cx="8" cy="5" r="3"/><path d="M2 14c0-3 3-5 6-5s6 2 6 5"/>', label: 'Visitors' },
]

const periods = [
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '30m', value: '30m' },
  { label: '1h', value: '1h' },
  { label: '6h', value: '6h' },
  { label: '24h', value: '24h' },
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
]

// ── Bind to store ──
const activeTab = computed(() => store.activeTab)
const period = computed(() => store.activePeriod)
const loading = computed(() => store.initialLoading)
const refreshing = computed(() => store.refreshing)

const cached = computed(() => store.data)
const stats = computed(() => cached.value.stats || [])
const chartData = computed(() => cached.value.chartData || [])
const topPages = computed(() => cached.value.topPages || [])
const sources = computed(() => cached.value.sources || [])
const devices = computed(() => cached.value.devices || [])
const countries = computed(() => cached.value.countries || [])
const realtimeVisitors = computed(() => cached.value.realtimeVisitors || 0)
const noData = computed(() => cached.value.noData)
const funnelList = computed(() => cached.value.funnelList || [])
const funnelResult = computed(() => cached.value.funnelResult)
const retentionData = computed(() => cached.value.retentionData || {})
const flowData = computed(() => cached.value.flowData || {})
const entryExitData = computed(() => cached.value.entryExitData || {})
const insightsData = computed(() => cached.value.insightsData || {})
const visitorList = computed(() => cached.value.visitorList || [])
const timelineEvents = computed(() => cached.value.timelineEvents || [])

// Local UI state
const showCreateFunnel = ref(false)
const newFunnel = ref({ name: '', steps: [{ name: '', type: 'url', value: '' }, { name: '', type: 'url', value: '' }] })

// ════════════ CHART.JS CONFIGURATIONS ════════════

// Traffic Overview — Line chart with gradient fill
const trafficChartData = computed(() => ({
  labels: chartData.value.map(d => d.label),
  datasets: [
    {
      label: 'Visitors',
      data: chartData.value.map(d => d.visitors || 0),
      borderColor: '#5B8DEF',
      backgroundColor: 'rgba(91, 141, 239, 0.08)',
      fill: true,
      tension: 0.4,
      borderWidth: 2.5,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHoverBackgroundColor: '#5B8DEF',
      pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 2,
    },
    {
      label: 'Page Views',
      data: chartData.value.map(d => d.pageviews || 0),
      borderColor: '#3498db',
      backgroundColor: 'rgba(52, 152, 219, 0.05)',
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHoverBackgroundColor: '#3498db',
      pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 2,
    },
  ],
}))

const trafficChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: true, position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle', padding: 20, boxWidth: 6 } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff',
      bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      displayColors: true,
      boxWidth: 8,
      boxHeight: 8,
      usePointStyle: true,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: { maxTicksLimit: 8, padding: 8 },
    },
    y: {
      grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 12 },
      beginAtZero: true,
    },
  },
}

// Sources — Horizontal Bar chart
const sourcesChartData = computed(() => ({
  labels: sources.value.map(s => s.name),
  datasets: [{
    label: 'Sessions',
    data: sources.value.map(s => s.sessions || 0),
    backgroundColor: ['#5B8DEF', '#34D399', '#A78BFA', '#F59E0B', '#6B7280', '#EC4899'],
    borderRadius: 4,
    barThickness: 22,
  }],
}))

const sourcesChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff',
      bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 8 },
      beginAtZero: true,
    },
    y: {
      grid: { display: false },
      border: { display: false },
      ticks: { padding: 8 },
    },
  },
}

// Devices — Doughnut chart
const deviceColors = ['#5B8DEF', '#34D399', '#A78BFA', '#F59E0B', '#6B7280']
const devicesChartData = computed(() => ({
  labels: devices.value.map(d => d.name),
  datasets: [{
    data: devices.value.map(d => d.pct || 0),
    backgroundColor: deviceColors.slice(0, devices.value.length),
    borderWidth: 0,
    hoverOffset: 6,
  }],
}))

const devicesChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: {
    legend: { display: true, position: 'right', labels: { usePointStyle: true, pointStyle: 'circle', padding: 14, boxWidth: 8, font: { size: 12 } } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff',
      bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed}%` },
    },
  },
}

// ════════════ UTILITY FUNCTIONS ════════════

const maxRetentionWeeks = computed(() => {
  if (!retentionData.value.rows?.length) return 0
  return Math.max(...retentionData.value.rows.map(r => r.weeks?.length || 0))
})

function retentionColor(pct) {
  if (pct >= 80) return 'rgba(39, 174, 96, 0.3)'
  if (pct >= 60) return 'rgba(39, 174, 96, 0.2)'
  if (pct >= 40) return 'rgba(201, 160, 80, 0.2)'
  if (pct >= 20) return 'rgba(231, 76, 60, 0.15)'
  if (pct > 0) return 'rgba(231, 76, 60, 0.1)'
  return 'transparent'
}

function eventBadge(type) {
  const map = { pageview: 'badge-info', click: 'badge-warning', scroll: 'badge-neutral', form_submit: 'badge-success', custom: 'badge-neutral', exit: 'badge-danger' }
  return map[type] || 'badge-neutral'
}

function formatDate(d) {
  if (!d) return '--'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatTime(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// ── Store-backed actions ──
function switchTab(tabId) {
  store.switchTab(tabId)
}

function changePeriod(p) {
  store.changePeriod(p)
}

async function runFunnel(fid) {
  await store.runFunnel(websiteId, fid, period.value)
}

async function createFunnel() {
  await store.createFunnel(websiteId, { name: newFunnel.value.name, steps: newFunnel.value.steps })
  showCreateFunnel.value = false
  newFunnel.value = { name: '', steps: [{ name: '', type: 'url', value: '' }, { name: '', type: 'url', value: '' }] }
}

async function loadTimeline(vid) {
  await store.loadTimeline(websiteId, vid)
}

// ── Save to sessionStorage when data changes ──
let saveTimer = null
watch(() => store.cache, () => {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => store.saveToSession(), 500)
}, { deep: true })

// ── Init ──
onMounted(async () => {
  store.init(websiteId, period.value)
  await store.fetchOverview(websiteId, period.value)
})

onBeforeUnmount(() => {
  store.saveToSession()
})
</script>

<style scoped>
.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; color: var(--text-muted); }
.refresh-indicator { display: flex; align-items: center; gap: 8px; padding: 6px 14px; font-size: var(--font-xs); color: var(--text-muted); }
.refresh-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--brand-accent); animation: pulse 1s infinite; }

/* ── Tabs ── */
.analytics-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 4px; overflow-x: auto; }
.atab { display: flex; align-items: center; gap: 6px; padding: 10px 16px; border: none; background: transparent; border-radius: var(--radius-md); font-size: var(--font-sm); font-weight: 600; color: var(--text-muted); cursor: pointer; transition: all 0.15s; white-space: nowrap; font-family: var(--font-family); }
.atab:hover { color: var(--text-primary); background: var(--bg-surface); }
.atab.active { background: var(--text-primary); color: var(--text-inverse); }
.atab-icon { width: 16px; height: 16px; flex-shrink: 0; }
.chart-container canvas { width: 100% !important; }

/* ── KPI Grid ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; transition: all var(--transition-base); }
.kpi-card:hover { border-color: var(--border-hover); box-shadow: var(--shadow-sm); }
.kpi-highlight { border-color: var(--brand-accent); background: linear-gradient(135deg, var(--bg-card) 0%, rgba(201, 160, 80, 0.04) 100%); }
.kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.kpi-label { font-size: var(--font-xs); font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-trend { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: var(--radius-full); }
.trend-up { color: var(--color-success); background: var(--color-success-bg); }
.trend-down { color: var(--color-danger); background: var(--color-danger-bg); }
.kpi-value { font-family: var(--font-display); font-size: var(--font-3xl); color: var(--text-primary); line-height: 1.1; }

/* ── Chart ── */
.chart-card { margin-bottom: 24px; }
.chart-legend { display: flex; gap: 16px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: var(--font-xs); color: var(--text-secondary); }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.area-chart-wrap { position: relative; margin-top: 12px; }
.area-chart-svg { width: 100%; height: 220px; display: block; }
.chart-tooltip { position: absolute; top: 10px; transform: translateX(-50%); background: var(--text-primary); color: var(--text-inverse); padding: 8px 14px; border-radius: var(--radius-md); font-size: var(--font-xs); white-space: nowrap; z-index: 10; box-shadow: var(--shadow-md); pointer-events: none; }
.area-chart-labels { display: flex; justify-content: space-between; padding: 8px 0 0; font-size: 10px; color: var(--text-muted); }
.area-chart-labels .highlighted { color: var(--text-secondary); font-weight: 600; }

/* ── Layout ── */
.analytics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }

/* ── Channels ── */
.channel-list { display: flex; flex-direction: column; gap: 14px; }
.channel-item { display: flex; align-items: center; gap: 14px; }
.channel-info { min-width: 130px; }
.channel-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); display: block; }
.channel-bar-wrap { flex: 1; height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.channel-bar { height: 100%; border-radius: var(--radius-full); transition: width var(--transition-slow); }
.channel-pct { font-size: var(--font-sm); font-weight: 700; color: var(--text-primary); min-width: 36px; text-align: right; }

/* ── Pages ── */
.page-rank { width: 22px; height: 22px; background: var(--bg-surface); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-right: 8px; }

/* ── Devices ── */
.device-breakdown { display: flex; align-items: center; gap: 28px; }
.donut-chart { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.donut-chart svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.device-legend { display: flex; flex-direction: column; gap: 10px; flex: 1; }
.device-legend-item { display: flex; align-items: center; gap: 10px; font-size: var(--font-sm); }
.device-name { flex: 1; color: var(--text-secondary); }
.device-value { color: var(--text-primary); }

/* ── Countries ── */
.country-list { display: flex; flex-direction: column; gap: 10px; }
.country-item { display: flex; align-items: center; gap: 12px; }
.country-rank { width: 22px; height: 22px; background: var(--bg-surface); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-muted); }
.country-info { flex: 1; }
.country-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.country-bar-wrap { height: 4px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.country-bar { height: 100%; background: var(--brand-accent); border-radius: var(--radius-full); }

/* ── Realtime ── */
.realtime-card { display: flex; align-items: center; gap: 12px; padding: 16px 24px; }
.realtime-dot { width: 10px; height: 10px; background: var(--color-success); border-radius: 50%; animation: pulse 2s infinite; }

/* ── Period Tabs ── */
.period-tabs { display: flex; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-full); overflow: hidden; }
.period-tab { padding: 6px 14px; font-size: var(--font-xs); font-weight: 600; color: var(--text-muted); background: transparent; border: none; cursor: pointer; transition: all var(--transition-fast); font-family: var(--font-family); }
.period-tab:hover { color: var(--text-primary); }
.period-tab.active { background: var(--brand-accent); color: #1a1a2e; }

/* ── Funnels ── */
.funnel-list { display: flex; flex-direction: column; gap: 8px; }
.funnel-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; background: var(--bg-surface); border-radius: var(--radius-md); cursor: pointer; transition: all 0.15s; }
.funnel-item:hover { background: var(--bg-card); border: 1px solid var(--border-hover); }
.funnel-viz { display: flex; gap: 4px; align-items: flex-end; padding: 20px 0; height: 200px; }
.funnel-step { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; height: 100%; }
.funnel-bar { width: 100%; background: rgba(201,160,80,0.08); border-radius: var(--radius-md) var(--radius-md) 0 0; position: relative; min-height: 20px; transition: height 0.5s; display: flex; align-items: flex-end; }
.funnel-bar-fill { width: 100%; height: 100%; background: linear-gradient(180deg, var(--brand-accent), rgba(201,160,80,0.3)); border-radius: var(--radius-md) var(--radius-md) 0 0; }
.funnel-step-info { text-align: center; }
.text-danger { color: var(--color-danger); }

/* ── Retention ── */
.retention-table { font-size: var(--font-xs); }
.retention-cell { text-align: center; font-weight: 600; font-size: 11px; min-width: 50px; }

/* ── Flows ── */
.flow-list { display: flex; flex-direction: column; gap: 10px; }
.flow-item { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border-color); font-size: var(--font-sm); }
.flow-item:last-child { border-bottom: none; }
.flow-page { background: var(--bg-surface); padding: 4px 10px; border-radius: var(--radius-sm); font-family: 'SF Mono', monospace; font-size: var(--font-xs); }
.flow-arrow { color: var(--text-muted); }
.flow-count { margin-left: auto; font-weight: 700; color: var(--text-primary); }
.flow-stat-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size: var(--font-sm); }
.flow-stat-item:last-child { border-bottom: none; }

/* ── AI Insights ── */
.insights-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.insight-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; transition: all 0.15s; }
.insight-card:hover { box-shadow: var(--shadow-sm); }
.insight-warning { border-left: 3px solid var(--color-warning); }
.insight-critical { border-left: 3px solid var(--color-danger); }
.insight-opportunity { border-left: 3px solid var(--color-success); }
.insight-info { border-left: 3px solid var(--color-info); }
.insight-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.insight-icon { font-size: 20px; }
.insight-badge { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: var(--radius-full); }
.ibadge-warning { background: rgba(243,156,18,0.12); color: var(--color-warning); }
.ibadge-critical { background: rgba(231,76,60,0.12); color: var(--color-danger); }
.ibadge-opportunity { background: rgba(39,174,96,0.12); color: var(--color-success); }
.ibadge-info { background: rgba(52,152,219,0.12); color: var(--color-info); }
.insight-metric { margin-left: auto; font-size: var(--font-md); font-weight: 700; color: var(--text-primary); }
.insight-title { font-size: var(--font-md); color: var(--text-primary); margin: 0 0 6px; }
.insight-desc { font-size: var(--font-sm); color: var(--text-secondary); line-height: 1.5; margin: 0 0 12px; }
.insight-action { display: flex; align-items: center; gap: 6px; font-size: var(--font-xs); color: var(--brand-accent); font-weight: 600; }

/* ── Actions ── */
.action-item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--border-color); }
.action-item:last-child { border-bottom: none; }
.action-priority { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 3px 10px; border-radius: var(--radius-full); }
.ap-critical { background: rgba(231,76,60,0.12); color: var(--color-danger); }
.ap-warning { background: rgba(243,156,18,0.12); color: var(--color-warning); }
.ap-opportunity { background: rgba(39,174,96,0.12); color: var(--color-success); }
.ap-info { background: rgba(52,152,219,0.12); color: var(--color-info); }

/* ── Visitors ── */
.clickable-row { cursor: pointer; transition: background 0.1s; }
.clickable-row:hover { background: var(--bg-surface); }
.visitor-id { font-family: 'SF Mono', monospace; font-size: var(--font-sm); color: var(--text-primary); }

/* ── Timeline ── */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.timeline-item:last-child { border-bottom: none; }
.timeline-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot-pageview { background: var(--color-info); }
.dot-click { background: var(--color-warning); }
.dot-scroll { background: var(--text-muted); }
.dot-form_submit { background: var(--color-success); }
.dot-exit { background: var(--color-danger); }
.dot-custom { background: var(--brand-accent); }
.timeline-content { display: flex; align-items: center; gap: 10px; flex: 1; }
.badge-sm { font-size: 10px; padding: 1px 6px; }

/* ── Empty ── */
.empty-state-card { text-align: center; padding: 60px 40px; background: var(--bg-card); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); margin-bottom: 24px; }
.empty-icon { margin-bottom: 20px; opacity: 0.7; }
.empty-title { font-size: var(--font-lg); color: var(--text-primary); margin: 0 0 10px; }
.empty-desc { font-size: var(--font-sm); color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px; line-height: 1.6; }
.empty-snippet { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px 20px; display: inline-block; margin-bottom: 16px; }
.empty-snippet code { font-size: var(--font-xs); color: var(--brand-accent); font-family: 'SF Mono', 'Fira Code', monospace; }
.empty-hint { font-size: var(--font-xs); color: var(--text-muted); }
.empty-inline { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: var(--font-sm); }

/* ── Modal ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-card { background: var(--bg-card); padding: 28px; border-radius: var(--radius-lg); width: 100%; box-shadow: var(--shadow-lg); }

/* ── Responsive ── */
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .analytics-row { grid-template-columns: 1fr; } .analytics-tabs { flex-wrap: wrap; } }
@media (max-width: 600px) { .kpi-grid { grid-template-columns: 1fr; } .insights-grid { grid-template-columns: 1fr; } }
</style>
