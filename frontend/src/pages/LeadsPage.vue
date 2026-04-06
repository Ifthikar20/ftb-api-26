<template>
  <div class="leads-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Leads</h1>
        <p class="page-subtitle">Track, score, and manage your website leads.</p>
      </div>
      <div class="header-actions">
        <select v-if="activeTab === 'table'" class="filter-select" v-model="statusFilter" @change="fetchData">
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

    <!-- ═══ AI Search — Glassmorphism ═══ -->
    <div class="ai-search-card">
      <div class="ai-search-inner">
        <div class="ai-search-header">
          <div class="ai-search-title">
            <svg class="ai-sparkle" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.4 7.2H22l-6 4.8 2.4 7.2L12 16.4l-6.4 4.8 2.4-7.2-6-4.8h7.6z"/></svg>
            <span>AI Lead Finder</span>
          </div>
          <span class="ai-badge">AI-POWERED</span>
        </div>
        <div class="ai-search-input-wrap">
          <input
            v-model="aiPrompt"
            class="ai-search-input"
            type="text"
            placeholder='Describe your ideal lead — e.g. "SaaS founders in Austin who tweet about growth marketing"'
            @keydown.enter="runAISearch"
          />
          <button class="ai-search-btn" @click="runAISearch" :disabled="aiSearching || !aiPrompt.trim()">
            <span v-if="aiSearching" class="ai-spinner"></span>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/></svg>
          </button>
        </div>
        <div class="ai-chips">
          <button class="ai-chip" @click="aiPrompt = 'SaaS founders in San Francisco'">SaaS founders in SF</button>
          <button class="ai-chip" @click="aiPrompt = 'Marketing directors at e-commerce companies'">E-com marketing directors</button>
          <button class="ai-chip" @click="aiPrompt = 'CTO at fintech startups raising Series A'">Fintech CTOs</button>
          <button class="ai-chip" @click="aiPrompt = 'VP of Engineering at healthcare startups'">Healthcare VPEs</button>
        </div>
        <div v-if="aiSearching" class="ai-search-progress">
          <div class="ai-progress-bar"><div class="ai-progress-fill"></div></div>
          <span class="ai-progress-text">Searching LinkedIn, X, and the web…</span>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="leads-tabs">
      <button class="leads-tab" :class="{ active: activeTab === 'table' }" @click="activeTab = 'table'">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
        Cards
      </button>
      <button class="leads-tab" :class="{ active: activeTab === 'pipeline' }" @click="activeTab = 'pipeline'">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h6v6H3zM15 3h6v6h-6zM9 15h6v6H9z"/><path d="M6 9v3h3M18 9v6h-3M9 18H6v-3" stroke-dasharray="2 2"/></svg>
        Pipeline
      </button>
    </div>

    <div v-if="loading" class="loading-state">Loading leads...</div>
    <div v-else-if="fetchError" class="leads-error-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger)" stroke-width="1.5" style="opacity:0.6"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <h3 class="error-title">Couldn't load leads</h3>
      <p class="error-desc">{{ fetchError }}</p>
      <button class="btn btn-secondary btn-sm" @click="fetchData" style="margin-top:12px">Try Again</button>
    </div>
    <!-- ════════════════ CARD VIEW ════════════════ -->
    <template v-else-if="activeTab === 'table'">
      <!-- Stats Pills -->
      <div class="stats-pills">
        <div class="stat-pill"><span class="stat-pill-dot" style="background:#3b82f6"></span> Total <strong>{{ allTableLeads.length }}</strong></div>
        <div class="stat-pill"><span class="stat-pill-dot" style="background:#ef4444"></span> Hot <strong>{{ hotCount }}</strong></div>
        <div class="stat-pill"><span class="stat-pill-dot" style="background:#f59e0b"></span> Avg <strong>{{ avgScore }}</strong></div>
        <div v-if="aiResults.length" class="stat-pill stat-pill-ai">
          <span class="stat-pill-dot" style="background:#8b5cf6"></span> AI Found <strong>{{ aiResults.length }}</strong>
          <button class="pill-clear" @click="clearAIResults">✕</button>
        </div>
      </div>

      <!-- Select All / Action Row -->
      <div v-if="allTableLeads.length" class="select-row">
        <label class="select-all-label">
          <input type="checkbox" class="modern-check" :checked="aiSelected.length === allTableLeads.length && allTableLeads.length > 0" @change="toggleAllAI" />
          <span>Select all {{ allTableLeads.length }}</span>
        </label>
        <div v-if="aiSelected.length" class="select-info">
          <span>{{ aiSelected.length }} selected</span>
        </div>
      </div>

      <!-- Lead Cards Grid -->
      <div class="lead-cards-grid">
        <div
          v-for="(lead, i) in sortedTableLeads"
          :key="lead._rowId || i"
          class="lead-card"
          :class="{ 'lead-card-selected': aiSelected.includes(i) }"
          :style="{ '--card-delay': i * 50 + 'ms' }"
          @click="openLeadDetail(lead)"
        >
          <!-- Checkbox -->
          <div class="lead-card-check" @click.stop>
            <input type="checkbox" class="modern-check" :checked="aiSelected.includes(i)" @change="toggleAiSelect(i)" />
          </div>

          <!-- Avatar + Score -->
          <div class="lead-card-top">
            <div class="lead-avatar" :class="scoreTier(lead.relevance_score || lead.score || 0)">
              <span class="lead-initials">{{ initials(lead) }}</span>
              <svg class="score-ring" width="48" height="48" viewBox="0 0 48 48">
                <circle cx="24" cy="24" r="21" fill="none" stroke="var(--ring-track)" stroke-width="3" />
                <circle cx="24" cy="24" r="21" fill="none" stroke="var(--ring-color)" stroke-width="3"
                  :stroke-dasharray="132"
                  :stroke-dashoffset="132 - (132 * (lead.relevance_score || lead.score || 0) / 100)"
                  stroke-linecap="round"
                  transform="rotate(-90 24 24)"
                />
              </svg>
            </div>
            <div class="lead-card-identity">
              <span class="lead-card-name">{{ lead.name || 'Anonymous' }}</span>
              <span class="lead-card-role" v-if="lead.title">{{ lead.title }}</span>
            </div>
            <span class="lead-card-score" :class="scoreTier(lead.relevance_score || lead.score || 0)">{{ lead.relevance_score || lead.score || 0 }}</span>
          </div>

          <!-- Details -->
          <div class="lead-card-details">
            <div class="lead-detail-row" v-if="lead.company">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 21v-4h6v4"/></svg>
              <span>{{ lead.company }}</span>
            </div>
            <div class="lead-detail-row" v-if="lead.email">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 7l10 7 10-7"/></svg>
              <span class="detail-email">{{ lead.email }}</span>
            </div>
            <div class="lead-detail-row" v-if="lead.location">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2C8.1 2 5 5.1 5 9c0 5.2 7 13 7 13s7-7.8 7-13c0-3.9-3.1-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
              <span>{{ lead.location }}</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="lead-card-footer">
            <span class="src-tag" :class="'src-' + (lead.source || 'ai')">{{ (lead.source || 'ai').toUpperCase() }}</span>
            <div class="lead-card-links">
              <a v-if="lead.linkedin_url" :href="lead.linkedin_url" target="_blank" class="card-link" title="LinkedIn" @click.stop>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146zm4.943 12.248V6.169H2.542v7.225h2.401zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248-.015-.709-.52-1.248-1.342-1.248-.822 0-1.359.54-1.359 1.248 0 .694.521 1.248 1.327 1.248h.016zm4.908 8.212V9.359c0-.216.016-.432.08-.586.173-.431.568-.878 1.232-.878.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252-1.274 0-1.845.7-2.165 1.193V6.169H6.29c.032.68 0 7.225 0 7.225h2.361z"/></svg>
              </a>
              <a v-if="lead.twitter_url" :href="lead.twitter_url" target="_blank" class="card-link" title="X" @click.stop>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M5.026 15c6.038 0 9.341-5.003 9.341-9.334 0-.14 0-.282-.006-.422A6.685 6.685 0 0016 3.542a6.658 6.658 0 01-1.889.518 3.301 3.301 0 001.447-1.817 6.533 6.533 0 01-2.087.793A3.286 3.286 0 007.875 6.03 9.325 9.325 0 011.114 2.1 3.323 3.323 0 002.13 6.574A3.203 3.203 0 01.64 6.14v.04a3.288 3.288 0 002.632 3.218 3.203 3.203 0 01-.865.115c-.212 0-.418-.02-.62-.058a3.283 3.283 0 003.067 2.277A6.588 6.588 0 01.78 13.58a6.32 6.32 0 01-.78-.045A9.344 9.344 0 005.026 15z"/></svg>
              </a>
              <a v-if="lead.website || lead.company_url" :href="lead.website || lead.company_url" target="_blank" class="card-link" title="Website" @click.stop>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2a10 10 0 0 1 3 6 10 10 0 0 1-3 6 10 10 0 0 1-3-6 10 10 0 0 1 3-6z"/></svg>
              </a>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="allTableLeads.length === 0 && !aiSearching" class="lead-empty-state">
          <div class="empty-icon-wrap">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1"><circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/></svg>
          </div>
          <h3 class="empty-title">No leads yet</h3>
          <p class="empty-desc">Use the AI prompt above to discover leads, or they'll appear here as visitors interact with your site.</p>
        </div>
      </div>

      <!-- Why This Lead Matches -->
      <div v-if="aiSelected.length === 1 && aiResults.length" class="ai-reason-panel card">
        <div class="card-header"><h3 class="card-title" style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted)">Why This Lead Matches</h3></div>
        <p class="text-sm" style="color:var(--text-secondary);line-height:1.6;margin:0">{{ sortedTableLeads[aiSelected[0]]?.reason || 'No reason provided.' }}</p>
      </div>

      <!-- Sticky Action Bar -->
      <Transition name="action-bar">
        <div v-if="aiSelected.length > 0" class="sticky-action-bar">
          <div class="action-bar-inner">
            <span class="action-bar-count">{{ aiSelected.length }} lead{{ aiSelected.length > 1 ? 's' : '' }} selected</span>
            <div class="action-bar-buttons">
              <button class="action-btn action-btn-secondary" @click="aiSelected = []">Deselect All</button>
              <button class="action-btn action-btn-primary" @click="addSelectedToPipeline">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><path d="M1 4h4v4H1zM6 2h4v8H6zM11 5h4v3h-4z"/></svg>
                View in Pipeline →
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </template>

    <!-- ════════════════ PIPELINE VIEW ════════════════ -->
    <template v-else-if="activeTab === 'pipeline'">
      <!-- Empty state when pipeline has no nodes -->
      <div v-if="nodes.length === 0" class="pipeline-empty card">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1" style="opacity:0.4">
          <path d="M3 3h6v6H3zM15 3h6v6h-6zM9 15h6v6H9z"/><path d="M6 9v3h3M18 9v6h-3M9 18H6v-3" stroke-dasharray="2 2"/>
        </svg>
        <h3>No pipeline yet</h3>
        <p>Select leads from the Cards tab and click <strong>View in Pipeline →</strong> to start building your outreach flow.</p>
      </div>

      <div v-else class="pipeline-wrapper">
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
              <span class="cs-item-icon" v-html="c.icon"></span>
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

      <!-- Node Detail Panel — Mini-Card Layout -->
      <div class="pipeline-detail" v-if="selectedPipelineNode">
        <div class="pipeline-detail-header">
          <h3>{{ selectedPipelineNode.data.label }} <span class="badge badge-neutral">{{ filteredLeads.length }}</span></h3>
          <div class="pipeline-detail-actions">
            <button v-if="selectedPipelineNode.data.connectorId === 'send-email' && filteredLeads.length" class="btn btn-primary btn-sm" @click="bulkEmailFromPipeline">
              Send to All {{ filteredLeads.length }}
            </button>
            <button v-if="selectedPipelineNode.data.connectorId === 'linkedin-outreach' && filteredLeads.length" class="btn btn-secondary btn-sm" @click="openAllLinkedIn">
              Open All Profiles
            </button>
          </div>
        </div>
        <div class="pipeline-lead-cards">
          <div v-for="lead in filteredLeads" :key="lead.name || lead.email" class="pipeline-mini-card" @click="openLeadDetail(lead)">
            <div class="mini-card-avatar" :class="scoreTier(lead.relevance_score || lead.score || 0)">{{ initials(lead) }}</div>
            <div class="mini-card-info">
              <span class="mini-card-name">{{ lead.name || 'Anonymous' }}</span>
              <span class="mini-card-meta">{{ lead.company || '--' }} <span v-if="lead.email" class="mini-card-email">{{ lead.email }}</span></span>
            </div>
            <a v-if="selectedPipelineNode.data.connectorId === 'linkedin-outreach' && lead.linkedin_url" :href="lead.linkedin_url" target="_blank" class="btn btn-secondary btn-sm" @click.stop style="font-size:11px;padding:4px 10px">Open</a>
            <button v-else-if="selectedPipelineNode.data.connectorId === 'send-email' && lead.email" class="btn btn-secondary btn-sm" @click.stop="openEmailCompose(lead)" style="font-size:11px;padding:4px 10px">Draft</button>
            <span v-else class="mini-card-score" :class="scoreTier(lead.relevance_score || lead.score || 0)">{{ lead.relevance_score || lead.score || '--' }}</span>
          </div>
          <div v-if="filteredLeads.length === 0" class="text-sm text-muted" style="text-align:center;padding:24px">
            No leads in this node. Connect it to a source node to pass leads through.
          </div>
        </div>
      </div>
    </template>



    <!-- ══════════ Email Compose Modal ══════════ -->
    <div v-if="showEmailModal" class="modal-overlay" @click.self="showEmailModal = false">
      <div class="modal-content slide-up" style="max-width: 540px">
        <div class="modal-header">
          <h2 class="modal-title"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-3px;margin-right:6px"><rect x="1" y="3" width="14" height="10" rx="1.5"/><path d="M1 4l7 5 7-5"/></svg>Send Email</h2>
          <button class="btn-icon btn-ghost" @click="showEmailModal = false"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4l8 8M12 4l-8 8"/></svg></button>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px">
          <div class="form-group">
            <label class="form-label">To</label>
            <input class="form-input" :value="emailToAddress" disabled style="opacity:0.7" />
          </div>
          <div class="form-group">
            <label class="form-label">Subject</label>
            <input v-model="emailSubject" class="form-input" placeholder="Follow up on your visit" />
          </div>
          <div class="form-group">
            <label class="form-label">Message</label>
            <textarea v-model="emailBody" class="form-input" rows="6" placeholder="Hi there, I noticed you visited our pricing page..."></textarea>
          </div>
          <button class="btn btn-primary w-full" :disabled="emailSending || !emailSubject || !emailBody" @click="sendEmail">
            {{ emailSending ? 'Sending...' : 'Send Email' }}
          </button>
          <div v-if="emailSent" class="email-sent-msg"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-success);margin-right:6px;vertical-align:1px"></span>Email sent successfully!</div>
          <div v-if="emailError" class="email-error-msg"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-danger);margin-right:6px;vertical-align:1px"></span>{{ emailError }}</div>
        </div>
        <!-- Email History -->
        <div v-if="emailHistory.length" style="margin-top:20px;border-top:1px solid var(--border-color);padding-top:16px">
          <h4 style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin:0 0 10px">Previous Emails</h4>
          <div v-for="em in emailHistory" :key="em.id" class="email-history-item">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600;font-size:var(--font-sm)">{{ em.subject }}</span>
              <span class="badge" :class="em.status === 'sent' ? 'badge-success' : 'badge-danger'" style="font-size:9px">{{ em.status }}</span>
            </div>
            <div class="text-xs text-muted" style="margin-top:2px">{{ new Date(em.sent_at).toLocaleString() }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>



<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { useVueFlow } from '@vue-flow/core'
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
const { screenToFlowCoordinate: vfScreenToFlow } = useVueFlow()
const flowRef = ref(null)

const loading = ref(true)
const fetchError = ref('')
const leads = ref([])
const statusFilter = ref('')
const activeTab = ref('table')
const selectedNodeId = ref(null)
const selectedLead = ref(null)

// AI Lead Finder state
const aiPrompt = ref('')
const aiSearching = ref(false)
const aiSearchDone = ref(false)
const aiResults = ref([])
const aiMeta = ref({})

// AI table sorting & selection
const aiSortKey = ref('relevance_score')
const aiSortDir = ref('desc')
const aiSelected = ref([])

// Merge AI results with existing leads into a unified table
const allTableLeads = computed(() => {
  if (aiResults.value.length) {
    return aiResults.value.map((lead, i) => ({ ...lead, _rowId: 'ai-' + i, _isAI: true }))
  }
  return leads.value.map((lead, i) => ({
    ...lead,
    _rowId: lead.id || 'lead-' + i,
    _isAI: false,
    relevance_score: lead.score || 0,
    // Map backend field names to the display field names the template expects
    location: lead.location || lead.geo_country || '',
    title: lead.title || lead.device_type || '',
  }))
})

const sortedTableLeads = computed(() => {
  const arr = [...allTableLeads.value]
  const key = aiSortKey.value
  const dir = aiSortDir.value === 'asc' ? 1 : -1
  return arr.sort((a, b) => {
    const va = a[key] ?? ''
    const vb = b[key] ?? ''
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
})

// Keep sortedAIResults for backward compat in pipeline actions
const sortedAIResults = computed(() => sortedTableLeads.value)

function clearAIResults() {
  aiResults.value = []
  aiSelected.value = []
  aiSearchDone.value = false
  aiMeta.value = {}
}

function scoreColor(s) {
  if (s >= 80) return 'fill-high'
  if (s >= 60) return 'fill-mid'
  return 'fill-low'
}

function setAiSort(key) {
  if (aiSortKey.value === key) {
    aiSortDir.value = aiSortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    aiSortKey.value = key
    aiSortDir.value = key === 'relevance_score' ? 'desc' : 'asc'
  }
  aiSelected.value = [] // clear selection on re-sort
}

function toggleAiSelect(index) {
  const pos = aiSelected.value.indexOf(index)
  if (pos === -1) aiSelected.value.push(index)
  else aiSelected.value.splice(pos, 1)
}

function toggleAllAI() {
  if (aiSelected.value.length === sortedTableLeads.value.length) {
    aiSelected.value = []
  } else {
    aiSelected.value = sortedTableLeads.value.map((_, i) => i)
  }
}

function addSelectedToLeads() {
  // Now handled by the merged table — just clear selection
  aiSelected.value = []
}

function addSelectedToPipeline() {
  const selected = aiSelected.value.map(i => sortedTableLeads.value[i]).filter(Boolean)
  if (!selected.length) return

  // Reset pipeline to fresh state
  connectorCounter = 0
  pipelineLeadsData.value = selected

  nodes.value = [{
    id: 'source',
    type: 'pipeline',
    position: { x: 40, y: 120 },
    data: {
      nodeType: 'source',
      status: 'done',
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.5-7 8-7s8 3 8 7"/></svg>',
      label: 'Selected Leads',
      leadCount: selected.length,
      leads: selected,
    },
  }]
  edges.value = []
  selectedNodeId.value = 'source'
  aiSelected.value = []
  activeTab.value = 'pipeline'
}


// ── Pipeline leads data (the leads flowing through the pipeline) ──
const pipelineLeadsData = ref([])

// ── Connector catalog (simplified for execution pipeline) ──
const connectorCatalog = computed(() => {
  return {
    'Process': [
      { id: 'extract-email', nodeType: 'splitter', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 7l10 7 10-7"/></svg>', label: 'Extract Email', desc: 'Split by email availability', badgeClass: 'badge-info', hasSplit: true },
    ],
    'Outreach': [
      { id: 'send-email', nodeType: 'outreach', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/></svg>', label: 'Send Email', desc: 'Bulk or single email via SendGrid', badgeClass: 'badge-accent' },
      { id: 'linkedin-outreach', nodeType: 'linkedin', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146zm4.943 12.248V6.169H2.542v7.225h2.401zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248-.015-.709-.52-1.248-1.342-1.248-.822 0-1.359.54-1.359 1.248 0 .694.521 1.248 1.327 1.248h.016zm4.908 8.212V9.359c0-.216.016-.432.08-.586.173-.431.568-.878 1.232-.878.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252-1.274 0-1.845.7-2.165 1.193V6.169H6.29c.032.68 0 7.225 0 7.225h2.361z"/></svg>', label: 'LinkedIn Outreach', desc: 'Open profiles for manual DM', badgeClass: 'badge-info' },
    ],
    'Export': [
      { id: 'export-csv', nodeType: 'action', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M12 18v-6M9 15l3 3 3-3"/></svg>', label: 'Export CSV', desc: 'Download leads as CSV', badgeClass: 'badge-neutral' },
    ],
  }
})

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

// ── Vue Flow: Nodes & Edges (start empty, populated by addSelectedToPipeline) ──
const nodes = ref([])
const edges = ref([])

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

  // Convert screen coordinates to flow coordinates using the composable
  let position
  try {
    position = vfScreenToFlow({ x: event.clientX, y: event.clientY })
  } catch {
    // Fallback: manual offset calculation
    const connectorEl = flowRef.value?.$el || document.querySelector('.vue-flow')
    if (!connectorEl) return
    const bounds = connectorEl.getBoundingClientRect()
    position = { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
  }

  connectorCounter++
  const newId = `${draggedConnector.id}-${connectorCounter}`

  nodes.value.push({
    id: newId,
    type: 'pipeline',
    position,
    data: {
      nodeType: draggedConnector.nodeType || 'action',
      connectorId: draggedConnector.id,
      icon: draggedConnector.icon,
      label: draggedConnector.label,
      leadCount: undefined,
      leads: null,
      badge: draggedConnector.desc,
      badgeClass: draggedConnector.badgeClass || 'badge-neutral',
      status: 'idle',
      hasSplit: draggedConnector.hasSplit || false,
    },
  })

  draggedConnector = null
}

function onConnect(params) {
  const edgeId = `e-${params.source}-${params.target}`
  if (edges.value.find(e => e.id === edgeId)) return

  // Determine handle type (split vs primary)
  const sourceHandleId = params.sourceHandle || 'out'

  edges.value.push({
    id: edgeId,
    source: params.source,
    sourceHandle: sourceHandleId,
    target: params.target,
    animated: true,
    style: { stroke: sourceHandleId === 'split' ? 'var(--color-warning, #f59e0b)' : 'var(--brand-accent)', strokeWidth: 2 },
  })

  // ── DATA FLOW: propagate leads from source to target ──
  const sourceNode = nodes.value.find(n => n.id === params.source)
  const targetNode = nodes.value.find(n => n.id === params.target)
  if (!sourceNode?.data?.leads || !targetNode) return

  const srcLeads = sourceNode.data.leads

  // If connecting from a splitter's "split" handle, pass the remainder leads
  if (sourceHandleId === 'split' && sourceNode.data.splitLeads) {
    targetNode.data.leads = sourceNode.data.splitLeads
    targetNode.data.leadCount = sourceNode.data.splitLeads.length
    targetNode.data.status = 'ready'
  } else {
    // Primary output — pass main leads (or extracted leads for splitters)
    const mainLeads = sourceNode.data.mainLeads || srcLeads
    targetNode.data.leads = mainLeads
    targetNode.data.leadCount = mainLeads.length
    targetNode.data.status = 'ready'
  }

  // If the target is an extract-email splitter, auto execute the split
  if (targetNode.data.connectorId === 'extract-email') {
    executeSplit(targetNode)
  }
}

// ── Execute the email split on a node ──
function executeSplit(node) {
  if (!node.data.leads) return
  node.data.status = 'running'
  setTimeout(() => {
    const withEmail = node.data.leads.filter(l => l.email && l.email !== '--')
    const withoutEmail = node.data.leads.filter(l => !l.email || l.email === '--')
    node.data.mainLeads = withEmail
    node.data.splitLeads = withoutEmail
    node.data.leadCount = withEmail.length
    node.data.badge = `${withEmail.length} with email, ${withoutEmail.length} without`
    node.data.status = 'done'
  }, 800) // small delay for visual feedback
}

// ── Filtering & selection ──
const selectedPipelineNode = computed(() => {
  if (!selectedNodeId.value) return null
  return nodes.value.find(n => n.id === selectedNodeId.value)
})

const filteredLabel = computed(() => {
  const node = selectedPipelineNode.value
  if (!node) return 'Leads'
  return node.data?.label || 'Leads'
})

const filteredLeads = computed(() => {
  const node = selectedPipelineNode.value
  if (!node?.data?.leads) return []
  return node.data.leads
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
  fetchError.value = ''
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await leadsApi.list(websiteId, params)
    leads.value = data?.results || data?.data?.results || data?.data || data || []
  } catch (e) {
    fetchError.value = e.displayMessage || 'Failed to load leads. Please check your connection and try again.'
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  try { await leadsApi.export(websiteId) } catch {}
}

onMounted(fetchData)

// ── AI Lead Finder ──
async function runAISearch() {
  if (!aiPrompt.value.trim() || aiSearching.value) return
  aiSearching.value = true
  aiSearchDone.value = false
  aiResults.value = []
  aiSelected.value = []
  try {
    const { data } = await leadsApi.aiSearch(websiteId, { prompt: aiPrompt.value })
    aiResults.value = data?.leads || []
    aiMeta.value = data || {}
  } catch (e) {
    console.error('AI search failed', e)
  } finally {
    aiSearching.value = false
    aiSearchDone.value = true
  }
}

function addAILeadToTable(lead) {
  leads.value.unshift({
    id: 'ai-' + Date.now(),
    name: lead.name,
    email: '',
    company: lead.company || '',
    score: lead.relevance_score || 50,
    status: 'new',
    source: 'AI Finder',
  })
}

// ── Email Compose ──
const showEmailModal = ref(false)
const emailSubject = ref('')
const emailBody = ref('')
const emailSending = ref(false)
const emailSent = ref(false)
const emailError = ref('')
const emailHistory = ref([])
const emailLeadTarget = ref(null)

const emailToAddress = computed(() => emailLeadTarget.value?.email || 'No email')

async function openEmailCompose(lead) {
  emailLeadTarget.value = lead
  emailSubject.value = ''
  emailBody.value = ''
  emailSent.value = false
  emailError.value = ''
  emailHistory.value = []
  showEmailModal.value = true
  // Load email history
  try {
    const { data } = await leadsApi.getEmails(websiteId, lead.id)
    emailHistory.value = data || []
  } catch { /* ignore */ }
}

function bulkEmailFromPipeline() {
  const node = selectedPipelineNode.value
  if (!node?.data?.leads?.length) return
  // Open compose for the first lead with email — user sends to all
  const firstWithEmail = node.data.leads.find(l => l.email && l.email !== '--')
  if (firstWithEmail) openEmailCompose(firstWithEmail)
}

function openAllLinkedIn() {
  const node = selectedPipelineNode.value
  if (!node?.data?.leads?.length) return
  node.data.leads.forEach(l => {
    if (l.linkedin_url) window.open(l.linkedin_url, '_blank')
  })
}

async function sendEmail() {
  if (!emailSubject.value || !emailBody.value || !emailLeadTarget.value) return
  emailSending.value = true
  emailSent.value = false
  emailError.value = ''
  try {
    await leadsApi.sendEmail(websiteId, emailLeadTarget.value.id, {
      subject: emailSubject.value,
      body: emailBody.value,
    })
    emailSent.value = true
    emailSubject.value = ''
    emailBody.value = ''
    // Refresh history
    const { data } = await leadsApi.getEmails(websiteId, emailLeadTarget.value.id)
    emailHistory.value = data || []
  } catch (e) {
    emailError.value = e.response?.data?.error || 'Failed to send email'
  } finally {
    emailSending.value = false
  }
}
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* ── Error State ── */
.leads-error-state {
  text-align: center;
  padding: 80px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.error-title { margin: 0; font-size: var(--font-md); font-weight: 600; color: var(--text-primary); }
.error-desc { margin: 0; font-size: var(--font-sm); color: var(--text-muted); max-width: 340px; line-height: 1.5; }

/* ── Header ── */
.header-actions { display: flex; gap: 8px; align-items: center; }
.filter-select {
  padding: 6px 12px;
  font-size: var(--font-xs);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: var(--bg-card);
  color: var(--text-primary);
  cursor: pointer;
}

/* ═══════════════════════════════════════
   AI Search — Glassmorphism
   ═══════════════════════════════════════ */
.ai-search-card {
  margin-bottom: 24px;
  padding: 2px;
  border-radius: calc(var(--radius-lg) + 2px);
  background: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7, #6366f1);
  background-size: 300% 300%;
  animation: gradient-shift 6s ease infinite;
}

@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.ai-search-inner {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
}

.ai-search-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.ai-search-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
}

.ai-sparkle {
  color: #8b5cf6;
  animation: sparkle-pulse 2s ease-in-out infinite;
}

@keyframes sparkle-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.15); opacity: 0.7; }
}

.ai-badge {
  font-size: 0.55rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
}

.ai-search-input-wrap {
  display: flex;
  gap: 8px;
}

.ai-search-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: var(--font-sm);
  font-family: var(--font-family);
  background: var(--bg-surface);
  color: var(--text-primary);
  transition: all 0.25s ease;
}

.ai-search-input:focus {
  outline: none;
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15), 0 0 20px rgba(139, 92, 246, 0.06);
}

.ai-search-btn {
  padding: 0 18px;
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.ai-search-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); }
.ai-search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ai-chips {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.ai-chip {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: 0.68rem;
  font-family: var(--font-family);
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.ai-chip:hover {
  border-color: #8b5cf6;
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.04);
}

.ai-search-progress { margin-top: 12px; }
.ai-progress-bar { height: 3px; border-radius: 2px; background: var(--bg-surface); overflow: hidden; }
.ai-progress-fill {
  height: 100%;
  width: 40%;
  border-radius: 2px;
  background: linear-gradient(90deg, #8b5cf6, #6366f1);
  animation: progress-slide 1.5s ease-in-out infinite;
}
@keyframes progress-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}
.ai-progress-text { font-size: var(--font-xs); color: var(--text-muted); margin-top: 6px; display: block; }

/* ── Spinner ── */
@keyframes spin { to { transform: rotate(360deg); } }
.ai-spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* ═══════════════════════════════════════
   Tabs
   ═══════════════════════════════════════ */
.leads-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background: var(--bg-surface);
  padding: 4px;
  border-radius: var(--radius-md);
  width: fit-content;
}

.leads-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--font-xs);
  font-weight: 600;
  font-family: var(--font-family);
  cursor: pointer;
  transition: all 0.2s;
}

.leads-tab:hover { color: var(--text-primary); }
.leads-tab.active {
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

/* ═══════════════════════════════════════
   Stats Pills
   ═══════════════════════════════════════ */
.stats-pills {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  font-size: var(--font-xs);
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-pill strong {
  font-weight: 700;
  color: var(--text-primary);
}

.stat-pill-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stat-pill-ai { background: rgba(139, 92, 246, 0.06); border-color: rgba(139, 92, 246, 0.15); }
.pill-clear {
  margin-left: 4px;
  background: none; border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  padding: 0 2px;
}
.pill-clear:hover { color: var(--text-primary); }

/* ── Select Row ── */
.select-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 4px;
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  cursor: pointer;
}

.select-info { font-size: var(--font-xs); font-weight: 600; color: var(--brand-accent); }

.modern-check {
  width: 15px; height: 15px;
  cursor: pointer;
  accent-color: #8b5cf6;
}

/* ═══════════════════════════════════════
   Lead Cards Grid
   ═══════════════════════════════════════ */
.lead-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

@keyframes card-enter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.lead-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 18px 20px 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  animation: card-enter 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--card-delay, 0ms);
}

.lead-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
  border-color: var(--border-hover);
}

.lead-card-selected {
  border-color: #8b5cf6;
  box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.12);
}

.lead-card-check {
  position: absolute;
  top: 12px;
  right: 12px;
  opacity: 0;
  transition: opacity 0.15s;
}

.lead-card:hover .lead-card-check,
.lead-card-selected .lead-card-check { opacity: 1; }

/* ── Avatar + Score Ring ── */
.lead-card-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.lead-avatar {
  position: relative;
  width: 48px; height: 48px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lead-initials {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  z-index: 1;
}

.score-ring {
  position: absolute;
  top: 0; left: 0;
}

.score-hot   { --ring-color: #22c55e; --ring-track: rgba(34, 197, 94, 0.12); }
.score-warm  { --ring-color: #f59e0b; --ring-track: rgba(245, 158, 11, 0.12); }
.score-cold  { --ring-color: #94a3b8; --ring-track: rgba(148, 163, 184, 0.12); }

.lead-card-identity {
  flex: 1;
  min-width: 0;
}

.lead-card-name {
  display: block;
  font-weight: 700;
  font-size: var(--font-sm);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lead-card-role {
  display: block;
  font-size: 0.68rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}

.lead-card-score {
  font-size: 1.1rem;
  font-weight: 800;
  flex-shrink: 0;
}

.lead-card-score.score-hot  { color: #22c55e; }
.lead-card-score.score-warm { color: #f59e0b; }
.lead-card-score.score-cold { color: #94a3b8; }

/* ── Details ── */
.lead-card-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 50%, transparent);
}

.lead-detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-xs);
  color: var(--text-secondary);
}

.lead-detail-row svg { color: var(--text-muted); flex-shrink: 0; }
.detail-email { color: var(--brand-accent); }

/* ── Footer ── */
.lead-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lead-card-links { display: flex; gap: 4px; }
.card-link {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all 0.12s;
}
.card-link:hover { background: var(--bg-surface); color: var(--text-primary); }

/* ── Source Tag ── */
.src-tag {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
}
.src-ai { background: rgba(139, 92, 246, 0.08); color: #8b5cf6; }
.src-x { background: rgba(0,0,0,0.05); color: var(--text-secondary); }
.src-linkedin { background: rgba(10,102,194,0.08); color: #0a66c2; }
.src-web { background: rgba(148,163,184,0.08); color: var(--text-muted); }
.src-openclaw { background: rgba(34,197,94,0.08); color: #22c55e; }

/* ── Empty State ── */
.lead-empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
}
.empty-icon-wrap { margin-bottom: 12px; display: flex; justify-content: center; opacity: 0.35; }
.empty-title { margin: 0 0 6px; color: var(--text-primary); font-size: var(--font-md); font-weight: 600; }
.empty-desc { font-size: var(--font-sm); color: var(--text-muted); max-width: 340px; margin: 0 auto; line-height: 1.5; }

/* ═══════════════════════════════════════
   Sticky Action Bar
   ═══════════════════════════════════════ */
.sticky-action-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
}

.action-bar-inner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
  backdrop-filter: blur(12px);
}

.action-bar-count {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.action-bar-buttons { display: flex; gap: 8px; }

.action-btn {
  padding: 6px 16px;
  border-radius: var(--radius-full);
  font-size: var(--font-xs);
  font-weight: 600;
  font-family: var(--font-family);
  cursor: pointer;
  transition: all 0.15s;
  border: none;
  white-space: nowrap;
}

.action-btn-secondary {
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}
.action-btn-secondary:hover { border-color: var(--text-primary); color: var(--text-primary); }

.action-btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}
.action-btn-primary:hover { box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); transform: translateY(-1px); }

/* Action bar transition */
.action-bar-enter-active { transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); }
.action-bar-leave-active { transition: all 0.2s ease; }
.action-bar-enter-from,
.action-bar-leave-to { opacity: 0; transform: translateX(-50%) translateY(20px); }

/* ═══════════════════════════════════════
   Pipeline
   ═══════════════════════════════════════ */
.pipeline-empty {
  text-align: center;
  padding: 60px 20px;
}
.pipeline-empty h3 { margin: 12px 0 6px; font-size: var(--font-md); font-weight: 600; color: var(--text-primary); }
.pipeline-empty p { font-size: var(--font-sm); color: var(--text-muted); max-width: 380px; margin: 0 auto; line-height: 1.5; }

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

.cs-header { padding: 16px 14px 12px; border-bottom: 1px solid var(--border-color); }
.cs-title { font-size: var(--font-base); font-weight: 700; color: var(--text-primary); }
.cs-subtitle { font-size: var(--font-xs); color: var(--text-muted); margin-top: 2px; }
.cs-section { padding: 8px 0; }
.cs-section-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); padding: 4px 14px 6px; }
.cs-item { display: flex; align-items: center; gap: 10px; padding: 8px 14px; cursor: grab; transition: background var(--transition-fast); border-left: 3px solid transparent; }
.cs-item:hover { background: var(--bg-surface); border-left-color: var(--brand-accent); }
.cs-item:active { cursor: grabbing; }
.cs-item-icon { font-size: 18px; flex-shrink: 0; }
.cs-item-info { min-width: 0; }
.cs-item-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cs-item-desc { font-size: 10px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

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

/* ── Pipeline Detail Panel — Mini Cards ── */
.pipeline-detail {
  margin-top: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.pipeline-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.pipeline-detail-header h3 {
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.pipeline-detail-actions { display: flex; gap: 8px; }

.pipeline-lead-cards {
  padding: 12px 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.pipeline-mini-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  cursor: pointer;
  transition: all 0.15s;
}
.pipeline-mini-card:hover { background: var(--bg-hover); transform: translateX(2px); }

.mini-card-avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  color: white;
}
.mini-card-avatar.score-hot  { background: linear-gradient(135deg, #22c55e, #16a34a); }
.mini-card-avatar.score-warm { background: linear-gradient(135deg, #f59e0b, #d97706); }
.mini-card-avatar.score-cold { background: linear-gradient(135deg, #94a3b8, #64748b); }

.mini-card-info { flex: 1; min-width: 0; }
.mini-card-name { font-weight: 600; font-size: 12px; color: var(--text-primary); display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mini-card-meta { font-size: 11px; color: var(--text-muted); display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mini-card-email { margin-left: 4px; color: var(--brand-accent); }
.mini-card-score { font-size: 13px; font-weight: 700; }
.mini-card-score.score-hot  { color: #22c55e; }
.mini-card-score.score-warm { color: #f59e0b; }
.mini-card-score.score-cold { color: #94a3b8; }

/* ── Email Compose ── */
.email-sent-msg { text-align: center; padding: 8px; color: var(--color-success); font-size: var(--font-sm); font-weight: 600; }
.email-error-msg { text-align: center; padding: 8px; color: var(--color-danger); font-size: var(--font-sm); }
.email-history-item { padding: 10px 12px; background: var(--bg-surface); border-radius: var(--radius-sm); margin-bottom: 8px; }

/* ── Responsive ── */
@media (max-width: 900px) {
  .pipeline-wrapper { flex-direction: column; }
  .connector-sidebar { width: 100%; max-height: 200px; border-radius: var(--radius-lg) var(--radius-lg) 0 0; border-right: 1px solid var(--border-color); border-bottom: none; }
  .pipeline-canvas-wrap { border-radius: 0 0 var(--radius-lg) var(--radius-lg); }
  .lead-cards-grid { grid-template-columns: 1fr; }
  .pipeline-lead-cards { grid-template-columns: 1fr; }
}
</style>
