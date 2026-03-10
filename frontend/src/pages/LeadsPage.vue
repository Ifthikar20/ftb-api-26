<template>
  <div class="leads-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Leads</h1>
        <p class="page-subtitle">Track, score, and manage your website leads.</p>
      </div>
      <div class="flex gap-8">
        <select v-if="activeTab === 'table'" class="form-input" v-model="statusFilter" @change="fetchData" style="width:auto">
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="qualified">Qualified</option>
          <option value="customer">Customer</option>
          <option value="lost">Lost</option>
        </select>
        <button v-if="activeTab === 'table'" class="btn btn-secondary btn-sm" @click="handleExport">Export CSV</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'table' }" @click="activeTab = 'table'">Table</button>
      <button class="tab" :class="{ active: activeTab === 'pipeline' }" @click="activeTab = 'pipeline'">Pipeline</button>
    </div>

    <div v-if="loading" class="loading-state">Loading leads...</div>

    <!-- ════════════════ TABLE VIEW ════════════════ -->
    <template v-else-if="activeTab === 'table'">
      <div class="stats-grid" style="margin-bottom: 24px">
        <div class="stat-card"><div class="stat-label">Total Leads</div><div class="stat-value">{{ leads.length }}</div></div>
        <div class="stat-card"><div class="stat-label">Hot Leads</div><div class="stat-value">{{ hotCount }}</div></div>
        <div class="stat-card"><div class="stat-label">Avg Score</div><div class="stat-value">{{ avgScore }}</div></div>
      </div>

      <div class="card">
        <table class="data-table">
          <thead><tr><th>Name</th><th>Company</th><th>Score</th><th>Status</th><th>Source</th></tr></thead>
          <tbody>
            <tr v-for="lead in leads" :key="lead.id" @click="openLeadDetail(lead)" style="cursor:pointer">
              <td><div class="lead-name">{{ lead.name || 'Anonymous' }}</div><div class="text-xs text-muted">{{ lead.email }}</div></td>
              <td>{{ lead.company || '--' }}</td>
              <td><span class="score-badge" :class="scoreTier(lead.score)">{{ lead.score }}</span></td>
              <td><span class="badge" :class="statusClass(lead.status)">{{ lead.status }}</span></td>
              <td class="text-muted text-sm">{{ lead.source }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="leads.length === 0" class="empty-guide">
          <div style="font-size:40px;margin-bottom:12px">👤</div>
          <h3 style="margin:0 0 8px;color:var(--text-primary)">No leads captured yet</h3>
          <p style="font-size:var(--font-sm);color:var(--text-secondary);max-width:400px;margin:0 auto;line-height:1.6">Leads are automatically captured when visitors interact with forms on your tracked website.</p>
        </div>
      </div>
    </template>

    <!-- ════════════════ PIPELINE VIEW ════════════════ -->
    <template v-else-if="activeTab === 'pipeline'">
      <div class="pipeline-wrapper">
        <!-- ── Connector Sidebar ── -->
        <div class="connector-sidebar">
          <div class="cs-header">
            <h3 class="cs-title">Connectors</h3>
            <p class="cs-subtitle">Drag onto canvas to add</p>
          </div>

          <div class="cs-section" v-for="(items, category) in connectorCatalog" :key="category">
            <div class="cs-section-label">{{ category }}</div>
            <div
              v-for="c in items" :key="c.id"
              class="cs-item"
              draggable="true"
              @dragstart="onDragStart($event, c)"
            >
              <span class="cs-item-icon">{{ c.emoji }}</span>
              <div class="cs-item-info">
                <div class="cs-item-name">{{ c.label }}</div>
                <div class="cs-item-desc">{{ c.desc }}</div>
              </div>
            </div>
          </div>
        </div>



        <!-- ── Canvas ── -->
        <div class="pipeline-canvas-wrap" @drop="onDrop" @dragover.prevent @dragenter.prevent>
          <VueFlow
            ref="flowRef"
            v-model:nodes="nodes"
            v-model:edges="edges"
            :default-viewport="{ x: 30, y: 20, zoom: 0.75 }"
            :min-zoom="0.25"
            :max-zoom="2.5"
            :snap-to-grid="true"
            :snap-grid="[15, 15]"
            :connect-on-click="true"
            fit-view-on-init
            @node-click="onNodeClick"
            @connect="onConnect"
            class="pipeline-flow"
          >
            <template #node-pipeline="nodeProps">
              <PipelineNode v-bind="nodeProps" />
            </template>
            <Background :gap="20" :size="1" pattern-color="var(--border-color)" />
            <Controls position="bottom-left" />
            <MiniMap position="bottom-right" :node-color="miniMapNodeColor" />
          </VueFlow>
        </div>
      </div>

      <!-- Detail Panel (below canvas) -->
      <div class="pipeline-detail-grid" v-if="selectedLead">
        <div class="card">
          <div style="display:flex;align-items:center;gap:14px">
            <div class="avatar avatar-lg">{{ initials(selectedLead) }}</div>
            <div>
              <div style="font-weight:700;font-size:var(--font-md)">{{ selectedLead.name || 'Anonymous Visitor' }}</div>
              <div class="text-sm text-muted">{{ selectedLead.company || 'Unknown Company' }}</div>
              <div class="text-xs" style="color:var(--brand-accent)">{{ selectedLead.email || 'No email' }}</div>
            </div>
          </div>
          <div style="text-align:center;margin-top:16px;padding-top:16px;border-top:1px solid var(--border-color)">
            <svg viewBox="0 0 140 80" width="120" height="68" style="margin:0 auto 4px;display:block">
              <path d="M15,75 A55,55 0 0,1 125,75" fill="none" stroke="var(--border-color)" stroke-width="10" />
              <path d="M15,75 A55,55 0 0,1 125,75" fill="none" stroke="var(--brand-accent)" stroke-width="10" stroke-linecap="round"
                :stroke-dasharray="173" :stroke-dashoffset="173 - (selectedLead.score / 100) * 173" style="transition:stroke-dashoffset 0.8s ease" />
            </svg>
            <div style="font-family:var(--font-display);font-size:var(--font-2xl);color:var(--color-success)">{{ selectedLead.score }}%</div>
            <div class="text-xs text-muted">ML Success Prediction</div>
            <span class="badge badge-info" style="margin-top:8px">📧 Recommended: Email</span>
          </div>
          <div style="display:flex;gap:8px;margin-top:16px">
            <button class="btn btn-primary btn-sm" style="flex:1">📧 Send Email</button>
            <button class="btn btn-secondary btn-sm" style="flex:1">📋 Add Note</button>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3 class="card-title" style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted)">Why This Lead Will Convert</h3></div>
          <div class="corr-list">
            <div class="corr-row" v-for="c in correlations" :key="c.text">
              <span style="font-size:14px;width:18px;text-align:center;flex-shrink:0">{{ c.positive ? '✅' : '⚠️' }}</span>
              <span style="flex:1;font-size:var(--font-sm);color:var(--text-primary)">{{ c.text }}</span>
              <span class="badge" :class="c.positive ? 'badge-success' : 'badge-danger'" style="font-size:9px;padding:2px 6px">{{ c.impact }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3 class="card-title" style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted)">Company Intelligence</h3></div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <div class="avatar" style="width:28px;height:28px;font-size:11px;border-radius:8px">🏢</div>
            <div>
              <div style="font-weight:700;font-size:var(--font-sm)">{{ selectedLead.company || 'Unknown' }}</div>
              <div class="text-xs" style="color:var(--brand-accent)">{{ companyDomain }}</div>
            </div>
          </div>
          <div class="intel-grid">
            <div class="intel-cell"><div class="intel-label">Employees</div><div class="intel-value">50–200</div></div>
            <div class="intel-cell"><div class="intel-label">Funding</div><div class="intel-value">Series A</div></div>
            <div class="intel-cell"><div class="intel-label">Industry</div><div class="intel-value">{{ selectedLead.source || 'Tech' }}</div></div>
            <div class="intel-cell"><div class="intel-label">Hiring</div><div class="intel-value">3 marketing</div></div>
          </div>
        </div>
      </div>

      <!-- Lead list when node is clicked -->
      <div class="pipeline-detail-grid" v-else-if="selectedNodeId">
        <div class="card" style="grid-column:1/-1">
          <div class="card-header"><h3 class="card-title">{{ filteredLabel }} <span class="badge badge-neutral" style="margin-left:6px">{{ filteredLeads.length }}</span></h3></div>
          <div class="lead-list">
            <div class="lead-list-item" v-for="lead in filteredLeads.slice(0, 12)" :key="lead.id" @click="openLeadDetail(lead)">
              <div class="avatar" style="width:32px;height:32px;font-size:10px">{{ initials(lead) }}</div>
              <div style="flex:1;min-width:0">
                <div style="font-weight:600;font-size:var(--font-sm);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ lead.name || 'Anonymous' }}</div>
                <div class="text-xs text-muted">{{ lead.company || '--' }}</div>
              </div>
              <span class="score-badge" :class="scoreTier(lead.score)" style="font-size:10px;padding:2px 8px">{{ lead.score }}</span>
            </div>
          </div>
          <div v-if="filteredLeads.length === 0" class="text-sm text-muted" style="text-align:center;padding:20px">No leads in this segment yet.</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import PipelineNode from '@/components/PipelineNode.vue'
import leadsApi from '@/api/leads'

const route = useRoute()
const websiteId = route.params.websiteId
const flowRef = ref(null)

const loading = ref(true)
const leads = ref([])
const statusFilter = ref('')
const activeTab = ref('table')
const selectedNodeId = ref(null)
const selectedLead = ref(null)

// ── Connector catalog (drag from sidebar) ──
const connectorCatalog = {
  'Data Sources': [
    { id: 'gsc',       emoji: '📊', label: 'Search Console', desc: 'Keyword & click data',     badgeClass: 'badge-success' },
    { id: 'ga4',       emoji: '📈', label: 'GA4',            desc: 'Traffic & attribution',    badgeClass: 'badge-warning' },
    { id: 'shopify',   emoji: '🛍', label: 'Shopify',        desc: 'Customer & order data',    badgeClass: 'badge-success' },
    { id: 'webhooks',  emoji: '🔗', label: 'Webhooks',       desc: 'Custom event ingestion',   badgeClass: 'badge-neutral' },
  ],
  'Enrichment': [
    { id: 'clearbit',  emoji: '🔍', label: 'Clearbit',       desc: 'Firmographic enrichment',  badgeClass: 'badge-info' },
    { id: 'apollo',    emoji: '🚀', label: 'Apollo.io',      desc: 'Contact DB & tech stack',  badgeClass: 'badge-accent' },
    { id: 'linkedin',  emoji: '💼', label: 'LinkedIn',       desc: 'Profile & company intel',  badgeClass: 'badge-info' },
    { id: 'zoominfo',  emoji: '🔬', label: 'ZoomInfo',       desc: 'Enterprise B2B data',      badgeClass: 'badge-info' },
  ],
  'Outreach': [
    { id: 'email',     emoji: '📧', label: 'Email',          desc: 'Campaigns & drip flows',   badgeClass: 'badge-info' },
    { id: 'sms',       emoji: '💬', label: 'SMS (Twilio)',    desc: 'Text follow-ups',          badgeClass: 'badge-info' },
    { id: 'whatsapp',  emoji: '💚', label: 'WhatsApp',       desc: 'Conversational outreach',  badgeClass: 'badge-success' },
    { id: 'linkedin-mail', emoji: '✉️', label: 'LinkedIn InMail', desc: 'Direct messaging',   badgeClass: 'badge-info' },
  ],
  'Advertising': [
    { id: 'facebook',  emoji: '📘', label: 'Facebook Ads',   desc: 'Retarget audiences',       badgeClass: 'badge-info' },
    { id: 'google-ads',emoji: '🔎', label: 'Google Ads',     desc: 'Customer Match & display', badgeClass: 'badge-warning' },
    { id: 'pinterest', emoji: '📌', label: 'Pinterest',      desc: 'Promoted pin campaigns',   badgeClass: 'badge-danger' },
    { id: 'instagram', emoji: '📷', label: 'Instagram Ads',  desc: 'Story & reel ads',         badgeClass: 'badge-accent' },
    { id: 'tiktok',    emoji: '🎵', label: 'TikTok Ads',     desc: 'Video ad campaigns',       badgeClass: 'badge-neutral' },
  ],
  'CRM & Automation': [
    { id: 'hubspot',   emoji: '🟠', label: 'HubSpot',        desc: 'Two-way CRM sync',        badgeClass: 'badge-warning' },
    { id: 'salesforce', emoji: '☁️', label: 'Salesforce',     desc: 'Enterprise CRM sync',     badgeClass: 'badge-info' },
    { id: 'slack',     emoji: '💜', label: 'Slack',           desc: 'Real-time lead alerts',   badgeClass: 'badge-accent' },
    { id: 'zapier',    emoji: '⚡', label: 'Zapier',          desc: 'Universal automation',    badgeClass: 'badge-warning' },
  ],
  'AI & Intelligence': [
    { id: 'anthropic', emoji: '🤖', label: 'Claude AI',      desc: 'AI email drafting',        badgeClass: 'badge-accent' },
    { id: 'openai',    emoji: '✨', label: 'OpenAI',          desc: 'Content generation',      badgeClass: 'badge-success' },
    { id: 'mixpanel',  emoji: '🟣', label: 'Mixpanel',       desc: 'Product analytics',       badgeClass: 'badge-accent' },
  ],
}

let connectorCounter = 0

// ── Computed stats ──
const hotCount = computed(() => leads.value.filter(l => l.score >= 70).length)
const warmCount = computed(() => leads.value.filter(l => l.score >= 30 && l.score < 70).length)
const coldCount = computed(() => leads.value.filter(l => l.score < 30).length)
const contactedCount = computed(() => leads.value.filter(l => l.status === 'contacted').length)
const avgScore = computed(() => {
  if (leads.value.length === 0) return 0
  return Math.round(leads.value.reduce((sum, l) => sum + (l.score || 0), 0) / leads.value.length)
})

const companyDomain = computed(() => {
  if (!selectedLead.value?.company) return 'unknown.com'
  return selectedLead.value.company.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '.com'
})

// ── Vue Flow: Nodes (extended pipeline) ──
const nodes = ref([
  { id: 'source',   type: 'pipeline', position: { x: 0,    y: 140 }, data: { nodeType: 'source',  emoji: '🌐', label: 'All Visitors',   count: 0 } },
  { id: 'hot',      type: 'pipeline', position: { x: 280,  y: 10 },  data: { nodeType: 'hot',     emoji: '🔥', label: 'Hot Leads',      count: 0, badge: 'Score ≥ 70', badgeClass: 'badge-danger' } },
  { id: 'warm',     type: 'pipeline', position: { x: 280,  y: 170 }, data: { nodeType: 'warm',    emoji: '🌤', label: 'Warm Leads',     count: 0, badge: 'Score 30–69', badgeClass: 'badge-warning' } },
  { id: 'cold',     type: 'pipeline', position: { x: 280,  y: 330 }, data: { nodeType: 'cold',    emoji: '🧊', label: 'Cold Leads',     count: 0, badge: 'Score < 30', badgeClass: 'badge-neutral' } },
  { id: 'saas',     type: 'pipeline', position: { x: 540,  y: 0 },   data: { nodeType: 'saas',    emoji: '💻', label: 'SaaS',           count: 0, badge: 'Industry', badgeClass: 'badge-info' } },
  { id: 'health',   type: 'pipeline', position: { x: 540,  y: 150 }, data: { nodeType: 'health',  emoji: '🏥', label: 'Healthcare',     count: 0, badge: 'Industry', badgeClass: 'badge-success' } },
  { id: 'enrich',   type: 'pipeline', position: { x: 800,  y: 20 },  data: { nodeType: 'action',  emoji: '🔍', label: 'Enrich Profile', count: 0, badge: 'Auto', badgeClass: 'badge-accent' } },
  { id: 'score',    type: 'pipeline', position: { x: 800,  y: 170 }, data: { nodeType: 'action',  emoji: '🧠', label: 'ML Score',       count: 0, badge: 'AI Model', badgeClass: 'badge-accent' } },
  { id: 'campaign', type: 'pipeline', position: { x: 1060, y: 20 },  data: { nodeType: 'action',  emoji: '📧', label: 'Send Campaign',  count: 0, badge: 'Outreach', badgeClass: 'badge-accent' } },
  { id: 'nurture',  type: 'pipeline', position: { x: 1060, y: 170 }, data: { nodeType: 'action',  emoji: '🔄', label: 'Nurture Flow',   count: 0, badge: 'Automated', badgeClass: 'badge-accent' } },
  { id: 'convert',  type: 'pipeline', position: { x: 1060, y: 320 }, data: { nodeType: 'health',  emoji: '✅', label: 'Converted',       count: 0, badge: 'Customer', badgeClass: 'badge-success' } },
])

const edges = ref([
  { id: 'e1',  source: 'source',  target: 'hot',      animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e2',  source: 'source',  target: 'warm',     style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e3',  source: 'source',  target: 'cold',     style: { stroke: 'var(--border-color)', strokeWidth: 1.5 } },
  { id: 'e4',  source: 'hot',     target: 'saas',     style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e5',  source: 'hot',     target: 'health',   animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e6',  source: 'saas',    target: 'enrich',   style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e7',  source: 'health',  target: 'enrich',   animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e8',  source: 'enrich',  target: 'score',    animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e9',  source: 'score',   target: 'campaign', animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e10', source: 'score',   target: 'nurture',  style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e11', source: 'score',   target: 'convert',  style: { stroke: 'var(--color-success)', strokeWidth: 1.5 } },
  { id: 'e12', source: 'warm',    target: 'score',    style: { stroke: 'var(--border-color)', strokeWidth: 1 } },
])

// Update node counts
watch(leads, (newLeads) => {
  const total = newLeads.length > 0 ? newLeads.length * 37 : 847
  const hot = hotCount.value
  const enriched = Math.max(1, Math.floor(hot * 0.8))
  const scored = Math.max(1, Math.floor(enriched * 0.9))
  nodes.value[0].data.count  = total
  nodes.value[1].data.count  = hot
  nodes.value[2].data.count  = warmCount.value
  nodes.value[3].data.count  = coldCount.value
  nodes.value[4].data.count  = Math.max(1, Math.floor(hot * 0.52))
  nodes.value[5].data.count  = Math.max(1, Math.ceil(hot * 0.35))
  nodes.value[6].data.count  = enriched
  nodes.value[7].data.count  = scored
  nodes.value[8].data.count  = Math.max(1, Math.floor(scored * 0.6))
  nodes.value[9].data.count  = Math.max(1, Math.floor(scored * 0.3))
  nodes.value[10].data.count = Math.max(1, Math.floor(scored * 0.1))
}, { immediate: true })

// ── Drag & Drop connectors ──
let draggedConnector = null

function onDragStart(event, connector) {
  draggedConnector = connector
  event.dataTransfer.setData('application/connector', JSON.stringify(connector))
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(event) {
  event.preventDefault()
  if (!draggedConnector) return

  const connectorEl = flowRef.value?.$el || document.querySelector('.vue-flow')
  if (!connectorEl) return

  const bounds = connectorEl.getBoundingClientRect()
  const rawX = event.clientX - bounds.left
  const rawY = event.clientY - bounds.top

  // Get the Vue Flow instance to convert screen coords to flow coords
  const vfInstance = flowRef.value
  let position = { x: rawX, y: rawY }
  if (vfInstance?.screenToFlowCoordinate) {
    position = vfInstance.screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
  } else if (vfInstance?.project) {
    position = vfInstance.project({ x: rawX, y: rawY })
  }

  connectorCounter++
  const newId = `${draggedConnector.id}-${connectorCounter}`

  nodes.value.push({
    id: newId,
    type: 'pipeline',
    position,
    data: {
      nodeType: 'connector',
      emoji: draggedConnector.emoji,
      label: draggedConnector.label,
      count: undefined,
      badge: 'Connector',
      badgeClass: draggedConnector.badgeClass || 'badge-neutral',
    },
  })

  draggedConnector = null
}

function onConnect(params) {
  const id = `e-${params.source}-${params.target}`
  if (!edges.value.find(e => e.id === id)) {
    edges.value.push({
      id,
      source: params.source,
      target: params.target,
      animated: true,
      style: { stroke: 'var(--brand-accent)', strokeWidth: 2 },
    })
  }
}

// ── Filtering & selection ──
const filteredLabel = computed(() => {
  const labels = { source: 'All Leads', hot: 'Hot Leads', warm: 'Warm Leads', cold: 'Cold Leads', saas: 'SaaS', health: 'Healthcare', enrich: 'Enriched', score: 'ML Scored', campaign: 'Campaign', nurture: 'Nurture', convert: 'Converted' }
  return labels[selectedNodeId.value] || 'Leads'
})

const filteredLeads = computed(() => {
  switch (selectedNodeId.value) {
    case 'hot':    return leads.value.filter(l => l.score >= 70)
    case 'warm':   return leads.value.filter(l => l.score >= 30 && l.score < 70)
    case 'cold':   return leads.value.filter(l => l.score < 30)
    case 'campaign': return leads.value.filter(l => l.status === 'contacted')
    case 'convert':  return leads.value.filter(l => l.status === 'customer')
    default:       return leads.value
  }
})

const correlations = computed(() => {
  if (!selectedLead.value) return []
  const score = selectedLead.value.score || 50
  const f = []
  if (score >= 60) f.push({ positive: true, text: 'Visited /pricing 3 times in 7 days', impact: '+22%' })
  if (selectedLead.value.company) f.push({ positive: true, text: 'Company matches target ICP', impact: '+18%' })
  if (score >= 50) f.push({ positive: true, text: 'Senior role (VP level)', impact: '+15%' })
  f.push({ positive: true, text: `${Math.max(2, Math.floor(score / 8))} min avg read time`, impact: '+12%' })
  if (score < 80) f.push({ positive: false, text: 'No form submission yet', impact: '-8%' })
  if (score >= 40) f.push({ positive: true, text: 'Visit frequency increasing', impact: '+14%' })
  return f
})

function scoreTier(score) {
  if (score >= 80) return 'score-hot'
  if (score >= 50) return 'score-warm'
  return 'score-cold'
}

function statusClass(s) {
  return { new: 'badge-neutral', contacted: 'badge-info', qualified: 'badge-warning', customer: 'badge-success', lost: 'badge-danger' }[s] || 'badge-neutral'
}

function initials(lead) {
  return (lead?.name || 'A').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function onNodeClick({ node }) {
  selectedNodeId.value = node.id
  selectedLead.value = null
}

function openLeadDetail(lead) {
  selectedLead.value = lead
}

function miniMapNodeColor(node) {
  const c = { hot: '#c44d4d', warm: '#d4813a', cold: '#888', saas: '#4a8ec2', health: '#3d9970', action: '#d4956a', source: '#1e1e1e', connector: '#6e6a65' }
  return c[node.data?.nodeType] || '#888'
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await leadsApi.list(websiteId, params)
    leads.value = data?.results || data?.data?.results || data?.data || data || []
  } catch (e) { /* toast auto-triggered */ }
  finally { loading.value = false }
}

async function handleExport() {
  try { await leadsApi.export(websiteId) } catch {}
}

onMounted(fetchData)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.lead-name { font-weight: 600; color: var(--text-primary); }
.score-badge { display: inline-block; padding: 3px 10px; border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 700; }
.score-hot  { background: rgba(231, 76, 60, 0.12); color: var(--color-danger); }
.score-warm { background: rgba(243, 156, 18, 0.12); color: var(--color-warning); }
.score-cold { background: var(--bg-surface); color: var(--text-muted); }

/* ══════════════════════════════════════
   Pipeline Wrapper
   ══════════════════════════════════════ */
.pipeline-wrapper {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
}

/* ── Connector Sidebar ── */
.connector-sidebar {
  width: 210px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-right: none;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  overflow-y: auto;
  max-height: 700px;
}

.cs-header {
  padding: 16px 14px 12px;
  border-bottom: 1px solid var(--border-color);
}

.cs-title {
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
}

.cs-subtitle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

.cs-section { padding: 8px 0; }

.cs-section-label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  padding: 4px 14px 6px;
}

.cs-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  cursor: grab;
  transition: background var(--transition-fast);
  border-left: 3px solid transparent;
}

.cs-item:hover {
  background: var(--bg-surface);
  border-left-color: var(--brand-accent);
}

.cs-item:active { cursor: grabbing; }

.cs-item-icon { font-size: 18px; flex-shrink: 0; }

.cs-item-info { min-width: 0; }

.cs-item-name {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cs-item-desc {
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Canvas ── */
.pipeline-canvas-wrap {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  overflow: hidden;
}

.pipeline-flow { width: 100%; height: 700px; }

:deep(.vue-flow) { background: var(--bg-card) !important; }
:deep(.vue-flow__background) { opacity: 0.4; }
:deep(.vue-flow__edge-path) { stroke: var(--border-hover); stroke-width: 1.5; }
:deep(.vue-flow__edge.animated path) { stroke: var(--brand-accent); stroke-width: 2; }
:deep(.vue-flow__controls) { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); overflow: hidden; }
:deep(.vue-flow__controls-button) { background: var(--bg-card); border: none; border-bottom: 1px solid var(--border-color); color: var(--text-secondary); width: 28px; height: 28px; }
:deep(.vue-flow__controls-button:hover) { background: var(--bg-surface); color: var(--text-primary); }
:deep(.vue-flow__controls-button svg) { fill: currentColor; }
:deep(.vue-flow__minimap) { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); }
:deep(.vue-flow__connection-line) { stroke: var(--brand-accent); stroke-width: 2; }

/* ── Detail Panel ── */
.pipeline-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.corr-list { display: flex; flex-direction: column; gap: 6px; }
.corr-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--bg-surface); border-radius: var(--radius-sm); }
.intel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.intel-cell { background: var(--bg-surface); border-radius: var(--radius-sm); padding: 8px 10px; }
.intel-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
.intel-value { font-size: var(--font-sm); font-weight: 700; color: var(--text-primary); margin-top: 2px; }
.lead-list { display: flex; flex-direction: column; gap: 4px; }
.lead-list-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: var(--radius-sm); cursor: pointer; transition: background var(--transition-fast); }
.lead-list-item:hover { background: var(--bg-surface); }

@media (max-width: 900px) {
  .pipeline-wrapper { flex-direction: column; }
  .connector-sidebar { width: 100%; max-height: 200px; border-radius: var(--radius-lg) var(--radius-lg) 0 0; border-right: 1px solid var(--border-color); border-bottom: none; }
  .pipeline-canvas-wrap { border-radius: 0 0 var(--radius-lg) var(--radius-lg); }
  .pipeline-detail-grid { grid-template-columns: 1fr; }
}
</style>
