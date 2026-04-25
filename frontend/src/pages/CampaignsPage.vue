<template>
  <div class="campaigns-page fade-in">
    <!-- ═══ Page Header ═══ -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Campaigns</h1>
        <p class="page-subtitle">Create and send targeted email campaigns to your leads.</p>
      </div>
      <button class="btn btn-primary" @click="openCreate" id="btn-new-campaign">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="3" x2="8" y2="13"/><line x1="3" y1="8" x2="13" y2="8"/></svg>
        New Campaign
      </button>
    </div>

    <!-- ═══ Stats Strip ═══ -->
    <div class="stats-strip">
      <div class="stat-pill">
        <div class="stat-pill-icon" style="--pill-color: #6366f1">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3h12c.6 0 1 .4 1 1v8c0 .6-.4 1-1 1H2c-.6 0-1-.4-1-1V4c0-.6.4-1 1-1z"/><polyline points="14,4 8,9 2,4"/></svg>
        </div>
        <div>
          <div class="stat-pill-value">{{ campaigns.length }}</div>
          <div class="stat-pill-label">Total</div>
        </div>
      </div>
      <div class="stat-pill">
        <div class="stat-pill-icon" style="--pill-color: #22c55e">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 3L6 10l-3-3"/></svg>
        </div>
        <div>
          <div class="stat-pill-value">{{ sentCount }}</div>
          <div class="stat-pill-label">Sent</div>
        </div>
      </div>
      <div class="stat-pill">
        <div class="stat-pill-icon" style="--pill-color: #f59e0b">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v4l3 2"/><circle cx="8" cy="8" r="6"/></svg>
        </div>
        <div>
          <div class="stat-pill-value">{{ avgOpenRate }}%</div>
          <div class="stat-pill-label">Avg Open</div>
        </div>
      </div>
      <div class="stat-pill">
        <div class="stat-pill-icon" style="--pill-color: #3b82f6">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 8l6-6M11 2h4v4M11 9v5H2V5h5"/></svg>
        </div>
        <div>
          <div class="stat-pill-value">{{ avgClickRate }}%</div>
          <div class="stat-pill-label">Avg Click</div>
        </div>
      </div>
    </div>

    <!-- ═══ Loading ═══ -->
    <div v-if="loading" class="loading-state">
      <div class="loader-ring"></div>
      <span>Loading campaigns...</span>
    </div>

    <!-- ═══ Empty State ═══ -->
    <div v-else-if="campaigns.length === 0" class="empty-state-container">
      <div class="empty-state-card">
        <div class="empty-icon-wrap">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect x="4" y="12" width="48" height="32" rx="4" stroke="currentColor" stroke-width="2.5" opacity="0.3"/>
            <polyline points="4,14 28,32 52,14" fill="none" stroke="currentColor" stroke-width="2.5" opacity="0.5"/>
            <circle cx="28" cy="28" r="8" fill="none" stroke="var(--color-primary)" stroke-width="2.5"/>
            <line x1="28" y1="24" x2="28" y2="32" stroke="var(--color-primary)" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="24" y1="28" x2="32" y2="28" stroke="var(--color-primary)" stroke-width="2.5" stroke-linecap="round"/>
          </svg>
        </div>
        <h3 class="empty-title">No campaigns yet</h3>
        <p class="empty-desc">Create your first campaign to start reaching your leads with targeted email outreach.</p>
        <button class="btn btn-primary" @click="openCreate">Create Your First Campaign</button>
      </div>
    </div>

    <!-- ═══ Campaign List ═══ -->
    <div v-else class="campaigns-table-wrap">
      <!-- Filters -->
      <div class="table-toolbar">
        <div class="search-box">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="6" r="4.5"/><line x1="9.5" y1="9.5" x2="13" y2="13"/></svg>
          <input v-model="searchQuery" class="search-input" placeholder="Search campaigns..." />
        </div>
        <div class="filter-group">
          <select v-model="statusFilter" class="filter-select">
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="sending">Sending</option>
            <option value="sent">Sent</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      <!-- Table -->
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th class="sortable" @click="toggleSort('name')">
                Campaign
                <span v-if="sortField === 'name'" class="sort-arrow">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th>Status</th>
              <th class="sortable num" @click="toggleSort('recipient_count')">
                Sent
                <span v-if="sortField === 'recipient_count'" class="sort-arrow">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="num">Open Rate</th>
              <th class="num">Click Rate</th>
              <th class="sortable" @click="toggleSort('sent_at')">
                Date
                <span v-if="sortField === 'sent_at'" class="sort-arrow">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, idx) in filteredCampaigns" :key="c.id" class="table-row" :style="{ animationDelay: idx * 30 + 'ms' }">
              <td>
                <div class="campaign-cell">
                  <div class="campaign-cell-name">{{ c.name || c.subject }}</div>
                  <div class="campaign-cell-subject" v-if="c.name">{{ c.subject }}</div>
                </div>
              </td>
              <td><span class="badge" :class="statusBadge(c.status)">{{ c.status }}</span></td>
              <td class="num">{{ c.recipient_count || 0 }}</td>
              <td class="num">
                <div class="rate-cell">
                  <div class="rate-bar"><div class="rate-fill" :style="{ width: formatRate(c.open_rate) + '%', background: '#22c55e' }"></div></div>
                  <span>{{ formatRate(c.open_rate) }}%</span>
                </div>
              </td>
              <td class="num">
                <div class="rate-cell">
                  <div class="rate-bar"><div class="rate-fill" :style="{ width: formatRate(c.click_rate) + '%', background: '#3b82f6' }"></div></div>
                  <span>{{ formatRate(c.click_rate) }}%</span>
                </div>
              </td>
              <td>{{ c.sent_at ? formatDate(c.sent_at) : '—' }}</td>
              <td class="actions-col">
                <div class="action-btns">
                  <button v-if="c.status === 'draft'" class="btn-action btn-action-primary" @click="sendCampaign(c)" :disabled="sending === c.id" title="Send">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 1L1 6l5 2 2 5z"/></svg>
                  </button>
                  <button class="btn-action" @click="viewStats(c)" title="Stats">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="8" width="3" height="5" rx=".5"/><rect x="5.5" y="5" width="3" height="8" rx=".5"/><rect x="10" y="1" width="3" height="12" rx=".5"/></svg>
                  </button>
                  <button v-if="c.status === 'draft'" class="btn-action" @click="editCampaign(c)" title="Edit">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2l2 2L5 11H3V9z"/></svg>
                  </button>
                  <button class="btn-action btn-action-danger" @click="startDelete(c)" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4h10M5 4V2h4v2M3 4v8c0 .6.4 1 1 1h6c.6 0 1-.4 1-1V4"/></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ═══ Delete Confirmation ═══ -->
    <BaseModal v-model="showDeleteConfirm" title="Delete Campaign" max-width="420px">
      <p style="color: var(--text-secondary); font-size: var(--font-sm);">
        Are you sure you want to delete <strong>{{ deleteTarget?.name || deleteTarget?.subject }}</strong>? This action cannot be undone.
      </p>
      <template #footer>
        <button class="btn btn-secondary" @click="showDeleteConfirm = false">Cancel</button>
        <button class="btn btn-danger" @click="confirmDelete" :disabled="deleting">{{ deleting ? 'Deleting...' : 'Delete' }}</button>
      </template>
    </BaseModal>

    <!-- ═══ Campaign Wizard Modal ═══ -->
    <BaseModal v-model="showWizard" :title="wizardTitle" max-width="700px">
      <div class="wizard-container">
        <!-- Step Indicator -->
        <div class="wizard-steps">
          <div v-for="(step, i) in wizardStepLabels" :key="i"
               class="wizard-step"
               :class="{ active: wizardStep === i, done: wizardStep > i }"
               @click="wizardStep > i && (wizardStep = i)">
            <span class="wizard-step-num">{{ wizardStep > i ? '✓' : i + 1 }}</span>
            <span class="wizard-step-label">{{ step }}</span>
          </div>
        </div>

        <!-- Step 1: Details -->
        <div v-show="wizardStep === 0" class="wizard-body">
          <div class="form-group">
            <label class="form-label">Campaign Name</label>
            <input v-model="form.name" class="form-input" placeholder="e.g. March Outreach" />
          </div>
          <div class="form-group">
            <label class="form-label">Email Subject Line</label>
            <input v-model="form.subject" class="form-input" placeholder="e.g. We noticed you visited..." />
          </div>
          <div class="form-row">
            <div class="form-group flex-1">
              <label class="form-label">From Name</label>
              <input v-model="form.from_name" class="form-input" placeholder="e.g. FetchBot Team" />
            </div>
            <div class="form-group flex-1">
              <label class="form-label">From Email</label>
              <input v-model="form.from_email" class="form-input" placeholder="e.g. hello@yoursite.com" />
            </div>
          </div>
        </div>

        <!-- Step 2: Audience -->
        <div v-show="wizardStep === 1" class="wizard-body">
          <div class="form-group">
            <label class="form-label">Target Audience</label>
            <select v-model="form.segment" class="form-input" @change="loadRecipientPreview">
              <option :value="null">All leads with email</option>
              <option v-for="seg in segments" :key="seg.id" :value="seg.id">{{ seg.name }}</option>
            </select>
          </div>
          <div class="audience-preview">
            <div class="audience-count-wrap">
              <div class="audience-count" :class="{ pulse: loadingPreview }">
                {{ loadingPreview ? '...' : recipientPreview.recipient_count }}
              </div>
              <div class="audience-count-label">recipients</div>
            </div>
            <div class="audience-cost">
              <div class="cost-badge">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="5.5"/><path d="M7 4v6M5.5 5.5h2.5c.8 0 1.5.7 1.5 1.5s-.7 1.5-1.5 1.5H5"/></svg>
                Est. cost: ${{ recipientPreview.estimated_cost_usd || '0.00' }}
              </div>
              <div class="cost-note">~$0.40 per 1,000 emails via Resend (Pro plan)</div>
            </div>
          </div>
        </div>

        <!-- Step 3: Content -->
        <div v-show="wizardStep === 2" class="wizard-body">
          <div class="form-group">
            <div class="content-header">
              <label class="form-label">Email Body</label>
              <button class="btn-ai-assist" @click="showAIPrompt = !showAIPrompt" :class="{ active: showAIPrompt }">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="5" r="3"/><path d="M2 12c0-2.5 2.2-4 5-4s5 1.5 5 4"/><path d="M10 3l2-2M4 3L2 1" stroke-linecap="round"/></svg>
                AI Assist
              </button>
            </div>
            <!-- AI prompt input -->
            <div v-if="showAIPrompt" class="ai-prompt-section">
              <input v-model="aiPrompt" class="form-input ai-prompt-input"
                     placeholder="Describe your email... e.g. 'Follow-up email for leads who visited pricing page'"
                     @keydown.enter="generateAIBody" />
              <button class="btn btn-primary btn-sm" @click="generateAIBody" :disabled="generatingAI || !aiPrompt.trim()">
                {{ generatingAI ? 'Generating...' : 'Generate' }}
              </button>
            </div>
            <textarea v-model="form.body" class="form-input form-textarea" rows="10"
                      placeholder="Write your email body here (HTML supported)..."></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Canva Design URL <span class="optional-tag">(optional)</span></label>
            <input v-model="form.canva_design_url" class="form-input" placeholder="https://www.canva.com/design/..." />
          </div>

          <!-- A/B Test Toggle -->
          <div class="ab-toggle-section">
            <label class="toggle-row">
              <input type="checkbox" v-model="form.is_ab_test" class="toggle-checkbox" />
              <span class="toggle-slider"></span>
              <span class="toggle-label">Enable A/B Testing</span>
            </label>
          </div>
          <div v-if="form.is_ab_test" class="ab-fields">
            <div class="form-group">
              <label class="form-label">Subject Line B</label>
              <input v-model="form.subject_b" class="form-input" placeholder="Alternative subject line..." />
            </div>
            <div class="form-group">
              <label class="form-label">Body B</label>
              <textarea v-model="form.body_b" class="form-input form-textarea" rows="6" placeholder="Alternative email body..."></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">Split Ratio (% to Variant A)</label>
              <div class="split-slider-wrap">
                <input type="range" v-model.number="form.ab_split_ratio" min="10" max="90" step="5" class="split-slider" />
                <div class="split-labels">
                  <span class="split-a">A: {{ form.ab_split_ratio }}%</span>
                  <span class="split-b">B: {{ 100 - form.ab_split_ratio }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 4: Review -->
        <div v-show="wizardStep === 3" class="wizard-body">
          <div class="review-grid">
            <div class="review-item">
              <span class="review-label">Campaign</span>
              <span class="review-value">{{ form.name || '—' }}</span>
            </div>
            <div class="review-item">
              <span class="review-label">Subject</span>
              <span class="review-value">{{ form.subject || '—' }}</span>
            </div>
            <div class="review-item">
              <span class="review-label">From</span>
              <span class="review-value">{{ form.from_name || 'Default' }} &lt;{{ form.from_email || 'noreply' }}&gt;</span>
            </div>
            <div class="review-item">
              <span class="review-label">Recipients</span>
              <span class="review-value">{{ recipientPreview.recipient_count || 0 }} leads</span>
            </div>
            <div class="review-item">
              <span class="review-label">Est. Cost</span>
              <span class="review-value cost-highlight">${{ recipientPreview.estimated_cost_usd || '0.00' }}</span>
            </div>
            <div v-if="form.is_ab_test" class="review-item">
              <span class="review-label">A/B Test</span>
              <span class="review-value">{{ form.ab_split_ratio }}% A / {{ 100 - form.ab_split_ratio }}% B</span>
            </div>
          </div>

          <div class="review-preview">
            <div class="preview-label">Email Preview</div>
            <div class="preview-frame" v-html="form.body || '<p style=\'color:#999\'>No content yet</p>'"></div>
          </div>
        </div>
      </div>

      <p v-if="formError" class="form-error">{{ formError }}</p>

      <template #footer>
        <button v-if="wizardStep > 0" class="btn btn-secondary" @click="wizardStep--">Back</button>
        <div style="flex:1"></div>
        <button class="btn btn-secondary" @click="showWizard = false">Cancel</button>
        <button v-if="wizardStep < 3" class="btn btn-primary" @click="nextStep" :disabled="!canProceed">
          Next
        </button>
        <button v-else class="btn btn-primary" @click="saveCampaign" :disabled="saving">
          {{ saving ? 'Saving...' : (editing ? 'Save Changes' : 'Create Campaign') }}
        </button>
      </template>
    </BaseModal>

    <!-- ═══ Stats Modal ═══ -->
    <BaseModal :model-value="!!statsModal" @close="statsModal = null" :title="statsModal ? statsModal.name || statsModal.subject : ''" max-width="640px">
      <div v-if="loadingStats" class="loading-state"><div class="loader-ring"></div></div>
      <template v-else-if="stats">
        <!-- Stat cards -->
        <div class="stats-ring-grid">
          <div class="ring-card">
            <svg class="ring-svg" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="34" fill="none" stroke="var(--border-color)" stroke-width="6"/>
              <circle cx="40" cy="40" r="34" fill="none" stroke="#22c55e" stroke-width="6"
                :stroke-dasharray="ringDash(stats.open_rate)" stroke-dashoffset="0" stroke-linecap="round"
                transform="rotate(-90 40 40)" class="ring-progress"/>
            </svg>
            <div class="ring-center">
              <span class="ring-val">{{ stats.open_rate || 0 }}%</span>
              <span class="ring-label">Open Rate</span>
            </div>
          </div>
          <div class="ring-card">
            <svg class="ring-svg" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="34" fill="none" stroke="var(--border-color)" stroke-width="6"/>
              <circle cx="40" cy="40" r="34" fill="none" stroke="#3b82f6" stroke-width="6"
                :stroke-dasharray="ringDash(stats.click_rate)" stroke-dashoffset="0" stroke-linecap="round"
                transform="rotate(-90 40 40)" class="ring-progress"/>
            </svg>
            <div class="ring-center">
              <span class="ring-val">{{ stats.click_rate || 0 }}%</span>
              <span class="ring-label">Click Rate</span>
            </div>
          </div>
        </div>

        <div class="stats-detail-grid">
          <div class="sd-item"><span class="sd-count">{{ stats.sent || 0 }}</span><span class="sd-label">Sent</span></div>
          <div class="sd-item"><span class="sd-count" style="color:#22c55e">{{ stats.opened || 0 }}</span><span class="sd-label">Opened</span></div>
          <div class="sd-item"><span class="sd-count" style="color:#3b82f6">{{ stats.clicked || 0 }}</span><span class="sd-label">Clicked</span></div>
          <div class="sd-item"><span class="sd-count" style="color:#ef4444">{{ stats.bounced || 0 }}</span><span class="sd-label">Bounced</span></div>
          <div class="sd-item"><span class="sd-count" style="color:#f59e0b">{{ stats.failed || 0 }}</span><span class="sd-label">Failed</span></div>
        </div>

        <!-- A/B Comparison -->
        <div v-if="stats.variant_a" class="ab-comparison">
          <h4 class="ab-heading">A/B Test Results</h4>
          <div class="ab-grid">
            <div class="ab-card ab-variant-a">
              <div class="ab-variant-badge">A</div>
              <div class="ab-stat"><span class="ab-val">{{ stats.variant_a.recipients }}</span> recipients</div>
              <div class="ab-stat"><span class="ab-val" style="color:#22c55e">{{ stats.variant_a.open_rate }}%</span> opens</div>
              <div class="ab-stat"><span class="ab-val" style="color:#3b82f6">{{ stats.variant_a.click_rate }}%</span> clicks</div>
            </div>
            <div class="ab-card ab-variant-b">
              <div class="ab-variant-badge">B</div>
              <div class="ab-stat"><span class="ab-val">{{ stats.variant_b?.recipients || 0 }}</span> recipients</div>
              <div class="ab-stat"><span class="ab-val" style="color:#22c55e">{{ stats.variant_b?.open_rate || 0 }}%</span> opens</div>
              <div class="ab-stat"><span class="ab-val" style="color:#3b82f6">{{ stats.variant_b?.click_rate || 0 }}%</span> clicks</div>
            </div>
          </div>
        </div>

        <!-- Recipients table -->
        <div v-if="statsRecipients.length" class="recipients-section">
          <h4 class="section-subtitle">Recipients</h4>
          <div class="recipients-list">
            <div v-for="r in statsRecipients" :key="r.id" class="recipient-row">
              <div class="recipient-info">
                <span class="recipient-name">{{ r.lead_name || 'Unknown' }}</span>
                <span class="recipient-email">{{ r.lead_email }}</span>
              </div>
              <span class="badge" :class="recipientBadge(r.status)">{{ r.status }}</span>
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <button class="btn btn-secondary" @click="statsModal = null">Close</button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import campaignsApi from '@/api/campaigns'
import BaseModal from '@/components/ui/BaseModal.vue'

const route = useRoute()
const websiteId = route.params.websiteId
const toast = useToast()

// ── State ──
const campaigns = ref([])
const loading = ref(true)
const sending = ref(null)
const searchQuery = ref('')
const statusFilter = ref('')
const sortField = ref('created_at')
const sortDir = ref('desc')

// Wizard
const showWizard = ref(false)
const wizardStep = ref(0)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const wizardStepLabels = ['Details', 'Audience', 'Content', 'Review']

const form = ref(defaultForm())

// Segments & preview
const segments = ref([])
const loadingPreview = ref(false)
const recipientPreview = ref({ recipient_count: 0, estimated_cost_usd: 0 })

// AI
const showAIPrompt = ref(false)
const aiPrompt = ref('')
const generatingAI = ref(false)

// Delete
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Stats
const statsModal = ref(null)
const stats = ref(null)
const loadingStats = ref(false)
const statsRecipients = ref([])

function defaultForm() {
  return {
    name: '', subject: '', body: '', from_name: '', from_email: '',
    canva_design_url: '', segment: null,
    is_ab_test: false, subject_b: '', body_b: '', ab_split_ratio: 50,
  }
}

// ── Computed ──
const sentCount = computed(() => campaigns.value.filter(c => c.status === 'sent').length)

const avgOpenRate = computed(() => {
  const sent = campaigns.value.filter(c => c.open_rate != null && c.status === 'sent')
  if (!sent.length) return '0.0'
  return (sent.reduce((a, c) => a + (c.open_rate || 0), 0) / sent.length).toFixed(1)
})

const avgClickRate = computed(() => {
  const sent = campaigns.value.filter(c => c.click_rate != null && c.status === 'sent')
  if (!sent.length) return '0.0'
  return (sent.reduce((a, c) => a + (c.click_rate || 0), 0) / sent.length).toFixed(1)
})

const wizardTitle = computed(() => {
  if (editing.value) return 'Edit Campaign'
  return 'New Campaign'
})

const canProceed = computed(() => {
  if (wizardStep.value === 0) return form.value.name.trim() && form.value.subject.trim()
  if (wizardStep.value === 1) return true
  if (wizardStep.value === 2) return form.value.body.trim()
  return true
})

const filteredCampaigns = computed(() => {
  let result = [...campaigns.value]

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(c =>
      (c.name || '').toLowerCase().includes(q) ||
      (c.subject || '').toLowerCase().includes(q)
    )
  }

  if (statusFilter.value) {
    result = result.filter(c => c.status === statusFilter.value)
  }

  // Sort
  result.sort((a, b) => {
    const aVal = a[sortField.value] || ''
    const bVal = b[sortField.value] || ''
    const cmp = aVal > bVal ? 1 : aVal < bVal ? -1 : 0
    return sortDir.value === 'asc' ? cmp : -cmp
  })

  return result
})

// ── Methods ──
function statusBadge(status) {
  return {
    draft: 'badge-neutral',
    sending: 'badge-warning',
    sent: 'badge-success',
    failed: 'badge-danger'
  }[status] || 'badge-neutral'
}

function recipientBadge(status) {
  return {
    queued: 'badge-neutral',
    sent: 'badge-info',
    opened: 'badge-success',
    clicked: 'badge-primary',
    bounced: 'badge-danger',
    failed: 'badge-danger'
  }[status] || 'badge-neutral'
}

function formatRate(val) {
  return val != null ? Number(val).toFixed(1) : '0.0'
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function toggleSort(field) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'desc'
  }
}

function ringDash(rate) {
  const circ = 2 * Math.PI * 34  // ~213.6
  const filled = (rate || 0) / 100 * circ
  return `${filled} ${circ}`
}

// ── Wizard ──
function openCreate() {
  editing.value = null
  form.value = defaultForm()
  wizardStep.value = 0
  formError.value = ''
  showWizard.value = true
  loadSegments()
  loadRecipientPreview()
}

function editCampaign(c) {
  editing.value = c
  form.value = {
    name: c.name || '', subject: c.subject || '', body: c.body || '',
    from_name: c.from_name || '', from_email: c.from_email || '',
    canva_design_url: c.canva_design_url || '', segment: c.segment || null,
    is_ab_test: c.is_ab_test || false, subject_b: c.subject_b || '',
    body_b: c.body_b || '', ab_split_ratio: c.ab_split_ratio || 50,
  }
  wizardStep.value = 0
  formError.value = ''
  showWizard.value = true
  loadSegments()
  loadRecipientPreview()
}

function nextStep() {
  if (canProceed.value && wizardStep.value < 3) {
    wizardStep.value++
  }
}

async function loadSegments() {
  try {
    const { data } = await campaignsApi.segments(websiteId)
    segments.value = data?.results || data || []
  } catch {
    segments.value = []
  }
}

async function loadRecipientPreview() {
  loadingPreview.value = true
  try {
    const params = {}
    if (form.value.segment) params.segment_id = form.value.segment
    const { data } = await campaignsApi.previewRecipients(websiteId, params)
    recipientPreview.value = data?.data || data || { recipient_count: 0, estimated_cost_usd: 0 }
  } catch {
    recipientPreview.value = { recipient_count: 0, estimated_cost_usd: 0 }
  } finally {
    loadingPreview.value = false
  }
}

async function generateAIBody() {
  if (!aiPrompt.value.trim()) return
  generatingAI.value = true
  try {
    const { data } = await campaignsApi.aiGenerate(websiteId, { prompt: aiPrompt.value })
    const html = data?.body_html || data?.data?.body_html || ''
    if (html) {
      form.value.body = html
      showAIPrompt.value = false
      aiPrompt.value = ''
      toast.success('Email body generated!')
    }
  } catch (err) {
    toast.error(err.displayMessage || 'AI generation failed.')
  } finally {
    generatingAI.value = false
  }
}

async function saveCampaign() {
  if (!form.value.name || !form.value.subject) {
    formError.value = 'Campaign name and subject are required.'
    return
  }
  if (!form.value.body) {
    formError.value = 'Email body is required.'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const payload = {
      name: form.value.name,
      subject: form.value.subject,
      body: form.value.body,
      from_name: form.value.from_name,
      from_email: form.value.from_email,
      canva_design_url: form.value.canva_design_url,
      segment: form.value.segment,
      is_ab_test: form.value.is_ab_test,
      subject_b: form.value.subject_b,
      body_b: form.value.body_b,
      ab_split_ratio: form.value.ab_split_ratio,
    }
    if (editing.value) {
      const { data } = await campaignsApi.update(websiteId, editing.value.id, payload)
      const idx = campaigns.value.findIndex(c => c.id === editing.value.id)
      if (idx >= 0) campaigns.value[idx] = data?.data || data
      toast.success('Campaign updated!')
    } else {
      const { data } = await campaignsApi.create(websiteId, payload)
      campaigns.value.unshift(data?.data || data)
      toast.success('Campaign created!')
    }
    showWizard.value = false
  } catch (err) {
    formError.value = err.displayMessage || 'Failed to save campaign.'
  } finally {
    saving.value = false
  }
}

async function sendCampaign(c) {
  sending.value = c.id
  try {
    const { data } = await campaignsApi.send(websiteId, c.id)
    const updated = data?.data || data
    const idx = campaigns.value.findIndex(x => x.id === c.id)
    if (idx >= 0) campaigns.value[idx] = { ...campaigns.value[idx], ...updated, status: updated.status || 'sending' }
    toast.success('Campaign is being sent!')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to send campaign.')
  } finally {
    sending.value = null
  }
}

function startDelete(c) {
  deleteTarget.value = c
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await campaignsApi.delete(websiteId, deleteTarget.value.id)
    campaigns.value = campaigns.value.filter(x => x.id !== deleteTarget.value.id)
    toast.success('Campaign deleted.')
    showDeleteConfirm.value = false
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to delete campaign.')
  } finally {
    deleting.value = false
  }
}

async function viewStats(c) {
  statsModal.value = c
  stats.value = null
  statsRecipients.value = []
  loadingStats.value = true
  try {
    const [statsRes, recipientsRes] = await Promise.all([
      campaignsApi.stats(websiteId, c.id),
      campaignsApi.recipients(websiteId, c.id),
    ])
    stats.value = statsRes.data?.data || statsRes.data || {}
    statsRecipients.value = recipientsRes.data?.results || recipientsRes.data || []
  } catch {
    stats.value = {}
  } finally {
    loadingStats.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await campaignsApi.list(websiteId)
    campaigns.value = data?.results || data || []
  } catch (e) {
    console.error('Campaigns fetch error', e)
    campaigns.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
/* ═══ Page Layout ═══ */
.campaigns-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0;
}

.page-subtitle {
  color: var(--text-muted);
  font-size: var(--font-sm);
  margin: 4px 0 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  border: none;
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  font-size: var(--font-sm, 14px);
  padding: 10px 20px;
  transition: all 0.2s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4); }
.btn-primary:disabled { opacity: 0.6; transform: none; cursor: not-allowed; }

.btn-secondary {
  background: var(--bg-surface, #f0f0f0);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}
.btn-secondary:hover { background: var(--bg-card); }

.btn-danger { background: #ef4444; color: #fff; }
.btn-danger:hover { background: #dc2626; }
.btn-danger:disabled { opacity: 0.6; }

.btn-sm { padding: 6px 14px; font-size: 13px; }

/* ═══ Stats Strip ═══ */
.stats-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 18px 20px;
  transition: all 0.2s ease;
}

.stat-pill:hover {
  border-color: var(--pill-color, var(--border-color));
  box-shadow: 0 0 0 1px var(--pill-color, transparent), 0 4px 12px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}

.stat-pill-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--pill-color) 12%, transparent);
  color: var(--pill-color);
  flex-shrink: 0;
}

.stat-pill-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  line-height: 1;
}

.stat-pill-label {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
}

/* ═══ Loading ═══ */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 80px 20px;
  color: var(--text-muted);
  font-size: var(--font-sm);
}

.loader-ring {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ═══ Empty State ═══ */
.empty-state-container {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
}

.empty-state-card {
  text-align: center;
  max-width: 420px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  padding: 48px 40px;
}

.empty-icon-wrap {
  color: var(--text-muted);
  margin-bottom: 20px;
}

.empty-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.empty-desc {
  color: var(--text-muted);
  font-size: var(--font-sm);
  margin: 0 0 24px;
  line-height: 1.6;
}

/* ═══ Table ═══ */
.campaigns-table-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  overflow: hidden;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0 12px;
  flex: 1;
  max-width: 280px;
  color: var(--text-muted);
}

.search-input {
  border: none;
  background: none;
  outline: none;
  padding: 8px 0;
  font-size: 13px;
  color: var(--text-primary);
  width: 100%;
}

.filter-select {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
}

.table-container { overflow-x: auto; }

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
  user-select: none;
}

.data-table th.sortable { cursor: pointer; }
.data-table th.sortable:hover { color: var(--text-primary); }
.sort-arrow { margin-left: 4px; font-size: 10px; }

.data-table td {
  padding: 14px 16px;
  font-size: 14px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.data-table th.num, .data-table td.num { text-align: right; }
.data-table th.actions-col, .data-table td.actions-col { text-align: right; width: 1%; white-space: nowrap; }

.table-row {
  animation: rowFadeIn 0.35s ease both;
}

@keyframes rowFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.data-table tbody tr:hover { background: rgba(99, 102, 241, 0.03); }
.data-table tbody tr:last-child td { border-bottom: none; }

.campaign-cell-name {
  font-weight: 600;
  color: var(--text-primary);
}

.campaign-cell-subject {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Rate bars */
.rate-cell { display: flex; align-items: center; gap: 8px; justify-content: flex-end; }
.rate-bar { width: 48px; height: 6px; background: var(--bg-surface); border-radius: 3px; overflow: hidden; flex-shrink: 0; }
.rate-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.rate-cell span { min-width: 40px; font-size: 13px; }

/* Badges */
.badge {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
  letter-spacing: 0.02em;
}

.badge-neutral { background: color-mix(in srgb, var(--text-muted) 12%, transparent); color: var(--text-muted); }
.badge-success { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
.badge-warning { background: rgba(245, 158, 11, 0.12); color: #d97706; }
.badge-danger { background: rgba(239, 68, 68, 0.12); color: #dc2626; }
.badge-info { background: rgba(59, 130, 246, 0.12); color: #2563eb; }
.badge-primary { background: rgba(99, 102, 241, 0.12); color: #6366f1; }

/* Action buttons */
.action-btns { display: flex; gap: 4px; justify-content: flex-end; }

.btn-action {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 8px;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action:hover {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--border-color);
}

.btn-action-primary:hover { color: #6366f1; border-color: rgba(99, 102, 241, 0.3); }
.btn-action-danger:hover { color: #ef4444; border-color: rgba(239, 68, 68, 0.3); }
.btn-action:disabled { opacity: 0.4; cursor: not-allowed; }

/* ═══ Wizard ═══ */
.wizard-container { min-height: 300px; }

.wizard-steps {
  display: flex;
  gap: 4px;
  margin-bottom: 28px;
  padding: 4px;
  background: var(--bg-surface);
  border-radius: 12px;
}

.wizard-step {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 9px;
  font-size: 13px;
  color: var(--text-muted);
  cursor: default;
  transition: all 0.2s ease;
}

.wizard-step.done { cursor: pointer; }
.wizard-step.done:hover { background: rgba(99, 102, 241, 0.05); }

.wizard-step.active {
  background: var(--bg-card);
  color: var(--text-primary);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.wizard-step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--bg-surface);
  color: var(--text-muted);
  flex-shrink: 0;
}

.wizard-step.active .wizard-step-num {
  background: #6366f1;
  color: #fff;
}

.wizard-step.done .wizard-step-num {
  background: #22c55e;
  color: #fff;
}

.wizard-step-label { white-space: nowrap; }

.wizard-body { animation: wizardFade 0.25s ease; }
@keyframes wizardFade { from { opacity: 0; transform: translateX(12px); } to { opacity: 1; transform: translateX(0); } }

/* ═══ Form ═══ */
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 14px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-input:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08); }
.form-textarea { resize: vertical; min-height: 120px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; }
.form-row { display: flex; gap: 14px; }
.flex-1 { flex: 1; }
.form-error { color: #ef4444; font-size: 13px; margin-top: 8px; }
.optional-tag { color: var(--text-muted); font-weight: 400; }

/* AI Assist */
.content-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }

.btn-ai-assist {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-ai-assist:hover, .btn-ai-assist.active {
  border-color: #6366f1;
  color: #6366f1;
  background: rgba(99, 102, 241, 0.06);
}

.ai-prompt-section {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  animation: wizardFade 0.2s ease;
}

.ai-prompt-input { flex: 1; }

/* A/B Test */
.ab-toggle-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.toggle-checkbox { display: none; }

.toggle-slider {
  width: 40px;
  height: 22px;
  background: var(--bg-surface);
  border: 2px solid var(--border-color);
  border-radius: 11px;
  position: relative;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.toggle-slider::after {
  content: '';
  width: 14px;
  height: 14px;
  background: var(--text-muted);
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: all 0.2s ease;
}

.toggle-checkbox:checked + .toggle-slider {
  background: #6366f1;
  border-color: #6366f1;
}

.toggle-checkbox:checked + .toggle-slider::after {
  transform: translateX(18px);
  background: #fff;
}

.toggle-label { font-size: 14px; font-weight: 500; color: var(--text-primary); }

.ab-fields { margin-top: 16px; animation: wizardFade 0.25s ease; }

.split-slider-wrap { margin-top: 4px; }
.split-slider { width: 100%; accent-color: #6366f1; }
.split-labels { display: flex; justify-content: space-between; font-size: 12px; margin-top: 4px; }
.split-a { color: #6366f1; font-weight: 600; }
.split-b { color: #f59e0b; font-weight: 600; }

/* ═══ Audience Preview ═══ */
.audience-preview {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-top: 20px;
  padding: 24px;
  background: var(--bg-surface);
  border-radius: 14px;
  border: 1px solid var(--border-color);
}

.audience-count-wrap { text-align: center; }

.audience-count {
  font-size: 48px;
  font-weight: 800;
  color: #6366f1;
  line-height: 1;
  letter-spacing: -0.03em;
}

.audience-count.pulse { animation: pulse 1s ease infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.audience-count-label {
  font-size: 13px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 4px;
}

.audience-cost { flex: 1; }

.cost-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 8px;
  color: #16a34a;
  font-size: 14px;
  font-weight: 600;
}

.cost-note {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

/* ═══ Review ═══ */
.review-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}

.review-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.review-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 600; }
.review-value { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.cost-highlight { color: #16a34a; }

.review-preview { margin-top: 16px; }
.preview-label { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.06em; margin-bottom: 8px; }

.preview-frame {
  padding: 20px;
  background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  max-height: 240px;
  overflow-y: auto;
  font-size: 14px;
  color: #333;
  line-height: 1.6;
}

/* ═══ Stats Modal ═══ */
.stats-ring-grid {
  display: flex;
  gap: 24px;
  justify-content: center;
  margin-bottom: 24px;
}

.ring-card {
  position: relative;
  width: 120px;
  height: 120px;
}

.ring-svg { width: 120px; height: 120px; }

.ring-progress {
  transition: stroke-dasharray 1s ease;
}

.ring-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.ring-val { display: block; font-size: 20px; font-weight: 700; color: var(--text-primary); }
.ring-label { display: block; font-size: 10px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; }

.stats-detail-grid {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.sd-item {
  flex: 1;
  text-align: center;
  padding: 12px 8px;
  background: var(--bg-surface);
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.sd-count { display: block; font-size: 20px; font-weight: 700; color: var(--text-primary); }
.sd-label { display: block; font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-top: 2px; letter-spacing: 0.04em; }

/* A/B Comparison */
.ab-comparison { margin-bottom: 24px; }
.ab-heading { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px; }

.ab-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.ab-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.ab-variant-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 10px;
}

.ab-variant-a .ab-variant-badge { background: #6366f1; }
.ab-variant-b .ab-variant-badge { background: #f59e0b; }

.ab-stat { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
.ab-val { font-weight: 700; color: var(--text-primary); }

/* Recipients */
.recipients-section { margin-top: 16px; }
.section-subtitle { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px; }

.recipients-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 10px;
}

.recipient-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
}

.recipient-row:last-child { border-bottom: none; }

.recipient-info { display: flex; flex-direction: column; gap: 2px; }
.recipient-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.recipient-email { font-size: 12px; color: var(--text-muted); }

/* ═══ Responsive ═══ */
@media (max-width: 768px) {
  .stats-strip { grid-template-columns: 1fr 1fr; }
  .wizard-steps { flex-wrap: wrap; }
  .wizard-step-label { display: none; }
  .form-row { flex-direction: column; }
  .review-grid { grid-template-columns: 1fr; }
  .ab-grid { grid-template-columns: 1fr; }
  .stats-detail-grid { flex-wrap: wrap; }
  .sd-item { min-width: 60px; }
}

/* ═══ Dark Mode Tweaks ═══ */
[data-theme="dark"] .preview-frame {
  background: #1e1e2e;
  color: #e0e0e0;
}

[data-theme="dark"] .stat-pill:hover {
  box-shadow: 0 0 0 1px var(--pill-color, transparent), 0 4px 12px rgba(0,0,0,0.2);
}
</style>
