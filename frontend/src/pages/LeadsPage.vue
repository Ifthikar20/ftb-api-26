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

    <!-- ═══ AI Prompt — Always Visible ═══ -->
    <div class="ai-search-card card">
      <h3 class="card-title" style="margin-bottom:4px">Describe your ideal lead</h3>
      <p class="text-sm text-muted" style="margin-bottom:16px">Use natural language to find leads from LinkedIn and Twitter profiles.</p>
      <textarea
        v-model="aiPrompt"
        class="ai-prompt-input"
        rows="3"
        placeholder='e.g. "SaaS founders in Austin who tweet about growth marketing" or "VP of Engineering at healthcare startups in NYC"'
        @keydown.meta.enter="runAISearch"
        @keydown.ctrl.enter="runAISearch"
      ></textarea>
      <div class="ai-search-actions">
        <div class="ai-example-prompts">
          <span class="text-xs text-muted">Try:</span>
          <button class="ai-example-btn" @click="aiPrompt = 'SaaS founders in San Francisco'">SaaS founders in SF</button>
          <button class="ai-example-btn" @click="aiPrompt = 'Marketing directors at e-commerce companies'">E-com marketing directors</button>
          <button class="ai-example-btn" @click="aiPrompt = 'CTO at fintech startups raising Series A'">Fintech CTOs</button>
        </div>
        <button class="btn btn-primary" @click="runAISearch" :disabled="aiSearching || !aiPrompt.trim()">
          <span v-if="aiSearching" class="ai-spinner"></span>
          {{ aiSearching ? 'Searching...' : 'Find Leads' }}
        </button>
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
        <div class="stat-card"><div class="stat-label">Total Leads</div><div class="stat-value">{{ allTableLeads.length }}</div></div>
        <div class="stat-card"><div class="stat-label">Hot Leads</div><div class="stat-value">{{ hotCount }}</div></div>
        <div class="stat-card"><div class="stat-label">Avg Score</div><div class="stat-value">{{ avgScore }}</div></div>
      </div>

      <!-- AI Search Loading -->
      <div v-if="aiSearching" class="ai-loading card" style="text-align:center;padding:32px">
        <div class="ai-spinner-lg"></div>
        <p class="text-sm text-muted" style="margin-top:12px">Searching X, LinkedIn, and the web for matching leads...</p>
      </div>

      <!-- AI Results Summary Bar -->
      <div v-if="aiResults.length" class="ai-table-bar" style="margin-bottom:16px">
        <div class="ai-table-bar-left">
          <h3 style="margin:0;font-size:var(--font-md)">{{ aiResults.length }} AI leads found</h3>
          <div class="ai-meta">
            <span v-if="aiMeta.sources_searched" class="text-xs text-muted">
              LinkedIn: {{ aiMeta.sources_searched.linkedin || 0 }} | X: {{ aiMeta.sources_searched.twitter || 0 }}<template v-if="aiMeta.sources_searched.web"> | Web: {{ aiMeta.sources_searched.web }}</template>
            </span>
            <span v-if="aiMeta.engine === 'openclaw'" class="badge badge-success" style="font-size:9px">OpenClaw</span>
            <span v-else-if="!aiMeta.has_google_search" class="badge badge-neutral" style="font-size:9px">AI-generated</span>
          </div>
        </div>
        <div class="ai-table-bar-right">
          <span v-if="aiSelected.length" class="text-sm" style="color:var(--brand-accent);font-weight:600">{{ aiSelected.length }} selected</span>
          <button class="btn btn-secondary btn-sm" :disabled="!aiSelected.length" @click="addSelectedToPipeline">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><path d="M1 4h4v4H1zM6 2h4v8H6zM11 5h4v3h-4z"/></svg>
            Add to Pipeline
          </button>
          <button class="btn btn-primary btn-sm" @click="clearAIResults" style="padding:4px 12px">Clear Results</button>
        </div>
      </div>

      <!-- Unified Leads Table -->
      <div class="card ai-table-card">
        <table class="data-table ai-data-table">
          <thead>
            <tr>
              <th style="width:32px" v-if="aiResults.length">
                <input type="checkbox" class="ai-check" :checked="aiSelected.length === allTableLeads.length && allTableLeads.length > 0" @change="toggleAllAI" />
              </th>
              <th class="sortable-th" @click="setAiSort('name')">
                Contact
                <span class="sort-icon" v-if="aiSortKey === 'name'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
              </th>
              <th class="sortable-th" @click="setAiSort('company')">
                Company
                <span class="sort-icon" v-if="aiSortKey === 'company'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
              </th>
              <th class="sortable-th" @click="setAiSort('email')">
                Email
                <span class="sort-icon" v-if="aiSortKey === 'email'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
              </th>
              <th class="sortable-th" @click="setAiSort('phone')" style="width:130px">Phone</th>
              <th class="sortable-th" @click="setAiSort('location')" style="width:130px">
                Location
                <span class="sort-icon" v-if="aiSortKey === 'location'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
              </th>
              <th class="sortable-th" @click="setAiSort('relevance_score')" style="width:72px">
                Score
                <span class="sort-icon" v-if="aiSortKey === 'relevance_score'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
              </th>
              <th style="width:56px">Src</th>
              <th style="width:72px"></th>
            </tr>
          </thead>
          <TransitionGroup name="table-row" tag="tbody">
            <tr v-for="(lead, i) in sortedTableLeads" :key="lead._rowId || i"
                :class="{ 'row-selected': aiSelected.includes(i) }"
                :style="{ '--row-delay': i * 40 + 'ms' }"
                @click="aiResults.length ? toggleAiSelect(i) : openLeadDetail(lead)"
                class="lead-row">
              <td v-if="aiResults.length" @click.stop>
                <input type="checkbox" class="ai-check" :checked="aiSelected.includes(i)" @change="toggleAiSelect(i)" />
              </td>
              <td>
                <div class="contact-cell">
                  <span class="contact-name">{{ lead.name || 'Anonymous' }}</span>
                  <span class="contact-role" v-if="lead.title">{{ lead.title }}</span>
                </div>
              </td>
              <td>
                <span class="company-text">{{ lead.company || '--' }}</span>
              </td>
              <td>
                <span class="email-text" :class="{ active: lead.email }">{{ lead.email || '--' }}</span>
              </td>
              <td class="mono-text">{{ lead.phone || '--' }}</td>
              <td class="dim-text">{{ lead.location || '--' }}</td>
              <td>
                <div class="score-cell">
                  <div class="score-bar">
                    <div class="score-fill" :class="scoreColor(lead.relevance_score || lead.score || 0)" :style="{ width: (lead.relevance_score || lead.score || 0) + '%' }"></div>
                  </div>
                  <span class="score-num">{{ lead.relevance_score || lead.score || 0 }}</span>
                </div>
              </td>
              <td><span class="src-tag" :class="'src-' + (lead.source || 'ai')">{{ (lead.source || 'ai').toUpperCase() }}</span></td>
              <td @click.stop>
                <div class="row-actions">
                  <a v-if="lead.linkedin_url" :href="lead.linkedin_url" target="_blank" class="row-link" title="LinkedIn">
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146zm4.943 12.248V6.169H2.542v7.225h2.401zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248-.015-.709-.52-1.248-1.342-1.248-.822 0-1.359.54-1.359 1.248 0 .694.521 1.248 1.327 1.248h.016zm4.908 8.212V9.359c0-.216.016-.432.08-.586.173-.431.568-.878 1.232-.878.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252-1.274 0-1.845.7-2.165 1.193V6.169H6.29c.032.68 0 7.225 0 7.225h2.361z"/></svg>
                  </a>
                  <a v-if="lead.twitter_url" :href="lead.twitter_url" target="_blank" class="row-link" title="X / Twitter">
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor"><path d="M5.026 15c6.038 0 9.341-5.003 9.341-9.334 0-.14 0-.282-.006-.422A6.685 6.685 0 0016 3.542a6.658 6.658 0 01-1.889.518 3.301 3.301 0 001.447-1.817 6.533 6.533 0 01-2.087.793A3.286 3.286 0 007.875 6.03 9.325 9.325 0 011.114 2.1 3.323 3.323 0 002.13 6.574A3.203 3.203 0 01.64 6.14v.04a3.288 3.288 0 002.632 3.218 3.203 3.203 0 01-.865.115c-.212 0-.418-.02-.62-.058a3.283 3.283 0 003.067 2.277A6.588 6.588 0 01.78 13.58a6.32 6.32 0 01-.78-.045A9.344 9.344 0 005.026 15z"/></svg>
                  </a>
                  <a v-if="lead.website || lead.company_url" :href="lead.website || lead.company_url" target="_blank" class="row-link" title="Website">
                    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2a10 10 0 0 1 3 6 10 10 0 0 1-3 6 10 10 0 0 1-3-6 10 10 0 0 1 3-6z"/></svg>
                  </a>
                </div>
              </td>
            </tr>
          </TransitionGroup>
        </table>
        <div v-if="allTableLeads.length === 0 && !aiSearching" class="empty-guide">
          <div class="empty-icon-wrap">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.2">
              <circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/>
            </svg>
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
    </template>

    <!-- ════════════════ PIPELINE VIEW ════════════════ -->
    <template v-else-if="activeTab === 'pipeline'">
      <!-- Empty state when pipeline has no nodes -->
      <div v-if="nodes.length === 0" class="card" style="text-align:center;padding:48px 20px">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.2" style="margin:0 auto 12px;display:block;opacity:0.45">
          <path d="M3 3h6v6H3zM15 3h6v6h-6zM9 15h6v6H9z"/><path d="M6 9v3h3M18 9v6h-3M9 18H6v-3" stroke-dasharray="2 2"/>
        </svg>
        <h3 style="margin:0 0 6px;font-size:var(--font-md);font-weight:600;color:var(--text-primary)">No pipeline yet</h3>
        <p style="font-size:var(--font-sm);color:var(--text-muted);max-width:340px;margin:0 auto;line-height:1.5">Select leads from the Table tab and click <strong>Add to Pipeline</strong> to start building your outreach flow.</p>
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

      <!-- Node Detail Panel (below canvas) -->
      <div class="pipeline-detail-grid" v-if="selectedPipelineNode">
        <div class="card" style="grid-column:1/-1">
          <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
            <h3 class="card-title">{{ selectedPipelineNode.data.label }} <span class="badge badge-neutral" style="margin-left:6px">{{ filteredLeads.length }}</span></h3>
            <!-- Action buttons based on node type -->
            <div style="display:flex;gap:8px">
              <button v-if="selectedPipelineNode.data.connectorId === 'send-email' && filteredLeads.length" class="btn btn-primary btn-sm" @click="bulkEmailFromPipeline">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/></svg>
                Send to All {{ filteredLeads.length }}
              </button>
              <button v-if="selectedPipelineNode.data.connectorId === 'linkedin-outreach' && filteredLeads.length" class="btn btn-secondary btn-sm" @click="openAllLinkedIn">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style="vertical-align:-2px;margin-right:4px"><path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146z"/></svg>
                Open All Profiles
              </button>
            </div>
          </div>
          <div class="lead-list">
            <div class="lead-list-item" v-for="lead in filteredLeads" :key="lead.name || lead.email" @click="openLeadDetail(lead)">
              <div style="flex:1;min-width:0">
                <div style="font-weight:600;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-primary)">{{ lead.name || 'Anonymous' }}</div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:1px">
                  {{ lead.company || '--' }}
                  <span v-if="lead.email" style="margin-left:6px;color:var(--brand-accent)">{{ lead.email }}</span>
                </div>
              </div>
              <!-- Per-lead actions -->
              <a v-if="selectedPipelineNode.data.connectorId === 'linkedin-outreach' && lead.linkedin_url" :href="lead.linkedin_url" target="_blank" class="btn btn-secondary btn-sm" @click.stop style="font-size:11px;padding:4px 10px">
                Open LinkedIn
              </a>
              <button v-else-if="selectedPipelineNode.data.connectorId === 'send-email' && lead.email" class="btn btn-secondary btn-sm" @click.stop="openEmailCompose(lead)" style="font-size:11px;padding:4px 10px">
                Draft Email
              </button>
              <span v-else-if="selectedPipelineNode.data.connectorId" class="score-num" style="font-size:12px">{{ lead.relevance_score || lead.score || '--' }}</span>
            </div>
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
  return leads.value.map((lead, i) => ({ ...lead, _rowId: lead.id || 'lead-' + i, _isAI: false, relevance_score: lead.score || 0 }))
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

/* ── Contact Cell (compact, inline) ── */
.contact-cell { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
.contact-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.contact-role {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
}
.contact-role::before { content: '\00B7'; margin-right: 5px; color: var(--border-color); }

/* ── Company ── */
.company-text { font-size: 13px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }

/* ── Email ── */
.email-text { font-size: 12px; color: var(--text-muted); }
.email-text.active { color: var(--brand-accent); }

/* ── Minor cells ── */
.mono-text { font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.dim-text { font-size: 12px; color: var(--text-muted); }

/* ── Score Bar ── */
.score-cell { display: flex; align-items: center; gap: 6px; width: 100%; }
.score-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-surface);
  border-radius: 2px;
  overflow: hidden;
  min-width: 28px;
}
.score-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.fill-high { background: var(--color-success, #22c55e); }
.fill-mid  { background: var(--color-warning, #f59e0b); }
.fill-low  { background: var(--text-muted); }
.score-num { font-size: 11px; font-weight: 600; color: var(--text-secondary); min-width: 18px; text-align: right; font-variant-numeric: tabular-nums; }

/* ── Source Tag ── */
.src-tag {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}
.src-ai { background: rgba(91,141,239,0.08); color: var(--brand-accent); }
.src-x { background: rgba(0,0,0,0.05); color: var(--text-secondary); }
.src-linkedin { background: rgba(10,102,194,0.08); color: #0a66c2; }
.src-web { background: rgba(148,163,184,0.08); color: var(--text-muted); }
.src-openclaw { background: rgba(34,197,94,0.08); color: #22c55e; }

/* ── Row Actions ── */
.row-actions { display: flex; gap: 2px; opacity: 0; transition: opacity 0.15s; }
.lead-row:hover .row-actions { opacity: 1; }
.row-link {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px;
  border-radius: 4px;
  color: var(--text-muted);
  transition: background 0.12s, color 0.12s;
}
.row-link:hover { background: var(--bg-surface); color: var(--text-primary); }

/* ── Row Animations ── */
@keyframes row-enter {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.lead-row {
  cursor: pointer;
  animation: row-enter 0.3s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--row-delay, 0ms);
}
.table-row-enter-active { animation: row-enter 0.25s cubic-bezier(0.22, 1, 0.36, 1) both; }
.table-row-leave-active { transition: opacity 0.15s, transform 0.15s; }
.table-row-leave-to { opacity: 0; transform: translateX(-8px); }
.table-row-move { transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1); }

/* ── Empty State ── */
.empty-guide { text-align: center; padding: 48px 20px; }
.empty-icon-wrap { margin-bottom: 12px; display: flex; justify-content: center; opacity: 0.45; }
.empty-title { margin: 0 0 6px; color: var(--text-primary); font-size: var(--font-md); font-weight: 600; }
.empty-desc { font-size: var(--font-sm); color: var(--text-muted); max-width: 340px; margin: 0 auto; line-height: 1.5; }

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
  .ai-results-grid { grid-template-columns: 1fr; }
}

/* ═══════════════════════════════════════
   AI Lead Finder
   ═══════════════════════════════════════ */
.ai-finder { max-width: 960px; }

.ai-search-card { margin-bottom: 24px; }

.ai-prompt-input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: var(--font-sm);
  font-family: var(--font-family);
  background: var(--bg-surface);
  color: var(--text-primary);
  resize: vertical;
  transition: border-color 0.2s;
}
.ai-prompt-input:focus {
  outline: none;
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px rgba(91, 141, 239, 0.1);
}

.ai-search-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  gap: 12px;
}

.ai-example-prompts {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.ai-example-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 4px 10px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-family);
}
.ai-example-btn:hover {
  border-color: var(--brand-accent);
  color: var(--brand-accent);
}

.ai-loading {
  text-align: center;
  padding: 60px 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.ai-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 6px;
  vertical-align: middle;
}
.ai-spinner-lg {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--brand-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.ai-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.ai-meta { display: flex; gap: 8px; align-items: center; }

.ai-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

@keyframes ai-card-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.ai-lead-card {
  animation: ai-card-in 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-lead-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ai-lead-name {
  font-weight: 700;
  font-size: var(--font-sm);
  color: var(--text-primary);
}
.ai-score {
  font-weight: 800;
  font-size: var(--font-lg);
  flex-shrink: 0;
}

.ai-lead-details {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.ai-lead-detail {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-xs);
  color: var(--text-secondary);
}

.ai-lead-reason {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
  border-left: 2px solid var(--brand-accent);
  padding-left: 8px;
}

.ai-lead-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.ai-social-links { display: flex; gap: 8px; }
.ai-social-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
}
.ai-social-link.li { background: rgba(10, 102, 194, 0.08); color: #0a66c2; }
.ai-social-link.li:hover { background: rgba(10, 102, 194, 0.18); }
.ai-social-link.tw { background: rgba(29, 161, 242, 0.08); color: #1da1f2; }
.ai-social-link.tw:hover { background: rgba(29, 161, 242, 0.18); }

.ai-empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

/* ── AI Sortable Results Table ── */
.ai-table-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.ai-table-bar-left { display: flex; flex-direction: column; gap: 4px; }
.ai-table-bar-right { display: flex; align-items: center; gap: 8px; }

.ai-table-card {
  overflow-x: auto;
  padding: 0;
  border-radius: var(--radius-lg);
}
.ai-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}
.ai-data-table thead { position: sticky; top: 0; z-index: 1; }
.ai-data-table th {
  background: var(--bg-card);
  padding: 9px 12px;
  text-align: left;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}
.sortable-th {
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}
.sortable-th:hover { color: var(--text-primary); }
.sort-icon {
  display: inline-block;
  font-size: 8px;
  margin-left: 2px;
  color: var(--brand-accent);
}

.ai-data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 50%, transparent);
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-data-table tbody tr {
  cursor: pointer;
  transition: background 0.12s ease;
}
.ai-data-table tbody tr:hover { background: var(--bg-hover); }
.ai-data-table tbody tr.row-selected { background: rgba(91, 141, 239, 0.04); }
.ai-data-table tbody tr.row-selected:hover { background: rgba(91, 141, 239, 0.08); }

.ai-check {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--brand-accent);
}

/* ── Email Compose ── */
.email-sent-msg { text-align: center; padding: 8px; color: var(--color-success); font-size: var(--font-sm); font-weight: 600; }
.email-error-msg { text-align: center; padding: 8px; color: var(--color-danger); font-size: var(--font-sm); }
.email-history-item { padding: 10px 12px; background: var(--bg-surface); border-radius: var(--radius-sm); margin-bottom: 8px; }
</style>
