<template>
  <div class="campaigns-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Campaigns</h1>
        <p class="page-subtitle">Create and send outbound email campaigns to your leads.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreate">New Campaign</button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading campaigns...</p>
    </div>

    <template v-else>
      <!-- Stats Row -->
      <div class="stats-grid" style="margin-bottom:24px">
        <div class="stat-card">
          <div class="stat-label">Total Campaigns</div>
          <div class="stat-value">{{ campaigns.length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Sent</div>
          <div class="stat-value">{{ sentCount }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Open Rate</div>
          <div class="stat-value">{{ avgOpenRate }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Click Rate</div>
          <div class="stat-value">{{ avgClickRate }}%</div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="campaigns.length === 0" class="empty-state card">
        <div class="empty-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        </div>
        <h3>No campaigns yet</h3>
        <p class="text-muted">Create your first campaign to start reaching your leads.</p>
        <button class="btn btn-primary" @click="openCreate">Create Campaign</button>
      </div>

      <!-- Campaign List -->
      <div v-else class="campaigns-list">
        <div v-for="campaign in campaigns" :key="campaign.id" class="card campaign-card">
          <div class="campaign-header">
            <div class="campaign-info">
              <div class="campaign-name">{{ campaign.name }}</div>
              <div class="campaign-subject text-muted text-sm">{{ campaign.subject }}</div>
            </div>
            <span class="badge" :class="statusBadge(campaign.status)">{{ campaign.status }}</span>
          </div>

          <div class="campaign-stats">
            <div class="cstat">
              <span class="cstat-val">{{ campaign.sent_count || 0 }}</span>
              <span class="cstat-label">Sent</span>
            </div>
            <div class="cstat">
              <span class="cstat-val">{{ formatRate(campaign.open_rate) }}%</span>
              <span class="cstat-label">Open rate</span>
            </div>
            <div class="cstat">
              <span class="cstat-val">{{ formatRate(campaign.click_rate) }}%</span>
              <span class="cstat-label">Click rate</span>
            </div>
            <div class="cstat">
              <span class="cstat-val">{{ campaign.sent_at ? formatDate(campaign.sent_at) : '—' }}</span>
              <span class="cstat-label">Sent at</span>
            </div>
          </div>

          <div class="campaign-actions">
            <button
              v-if="campaign.status === 'draft'"
              class="btn btn-primary btn-sm"
              @click="sendCampaign(campaign)"
              :disabled="sending === campaign.id"
            >
              {{ sending === campaign.id ? 'Sending...' : 'Send Now' }}
            </button>
            <button class="btn btn-secondary btn-sm" @click="viewStats(campaign)">Stats</button>
            <button
              v-if="campaign.status === 'draft'"
              class="btn btn-secondary btn-sm"
              @click="editCampaign(campaign)"
            >Edit</button>
            <button class="btn btn-ghost btn-sm" style="color:var(--color-danger)" @click="deleteCampaign(campaign)">Delete</button>
          </div>
        </div>
      </div>
    </template>

    <!-- Create / Edit Modal -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal-card" style="width:560px">
        <h3 class="card-title" style="margin-bottom:20px">{{ editing ? 'Edit Campaign' : 'New Campaign' }}</h3>
        <div style="margin-bottom:12px">
          <label class="form-label">Campaign Name</label>
          <input v-model="form.name" class="form-input" placeholder="e.g. March Outreach" />
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Email Subject</label>
          <input v-model="form.subject" class="form-input" placeholder="e.g. We noticed you visited..." />
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Email Body (HTML or plain text)</label>
          <textarea v-model="form.body_html" class="form-input" rows="6" placeholder="Hi {{name}}, ..."></textarea>
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Canva Design URL (optional)</label>
          <input v-model="form.canva_design_url" class="form-input" placeholder="https://www.canva.com/design/..." />
        </div>
        <div style="margin-bottom:20px">
          <label class="form-label">From Name</label>
          <input v-model="form.from_name" class="form-input" placeholder="e.g. GrowthPilot Team" />
        </div>
        <p v-if="formError" class="text-sm" style="color:var(--color-danger);margin-bottom:12px">{{ formError }}</p>
        <div class="flex gap-8" style="justify-content:flex-end">
          <button class="btn btn-secondary" @click="showForm = false">Cancel</button>
          <button class="btn btn-primary" @click="saveCampaign" :disabled="saving">
            {{ saving ? 'Saving...' : (editing ? 'Save Changes' : 'Create Campaign') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Modal -->
    <div v-if="statsModal" class="modal-overlay" @click.self="statsModal = null">
      <div class="modal-card" style="width:480px">
        <h3 class="card-title" style="margin-bottom:20px">Campaign Stats — {{ statsModal.name }}</h3>
        <div v-if="loadingStats" class="loading-state" style="padding:24px 0">Loading...</div>
        <template v-else-if="stats">
          <div class="stats-grid" style="grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
            <div class="stat-card"><div class="stat-label">Sent</div><div class="stat-value">{{ stats.sent_count }}</div></div>
            <div class="stat-card"><div class="stat-label">Opens</div><div class="stat-value">{{ stats.open_count }}</div></div>
            <div class="stat-card"><div class="stat-label">Clicks</div><div class="stat-value">{{ stats.click_count }}</div></div>
            <div class="stat-card"><div class="stat-label">Bounces</div><div class="stat-value">{{ stats.bounce_count || 0 }}</div></div>
          </div>
          <div class="flex gap-8" style="margin-bottom:8px">
            <div class="stat-card" style="flex:1"><div class="stat-label">Open Rate</div><div class="stat-value">{{ formatRate(stats.open_rate) }}%</div></div>
            <div class="stat-card" style="flex:1"><div class="stat-label">Click Rate</div><div class="stat-value">{{ formatRate(stats.click_rate) }}%</div></div>
          </div>
        </template>
        <div class="flex" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="statsModal = null">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import campaignsApi from '@/api/campaigns'

const props = defineProps({ websiteId: String })
const route = useRoute()
const toast = useToast()

const websiteId = computed(() => props.websiteId || route.params.websiteId)

const campaigns = ref([])
const loading = ref(true)
const sending = ref(null)
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const statsModal = ref(null)
const stats = ref(null)
const loadingStats = ref(false)

const form = ref({ name: '', subject: '', body_html: '', canva_design_url: '', from_name: '' })

const sentCount = computed(() => campaigns.value.filter(c => c.status === 'sent').length)
const avgOpenRate = computed(() => {
  const sent = campaigns.value.filter(c => c.open_rate != null)
  if (!sent.length) return '0.0'
  return (sent.reduce((a, c) => a + (c.open_rate || 0), 0) / sent.length).toFixed(1)
})
const avgClickRate = computed(() => {
  const sent = campaigns.value.filter(c => c.click_rate != null)
  if (!sent.length) return '0.0'
  return (sent.reduce((a, c) => a + (c.click_rate || 0), 0) / sent.length).toFixed(1)
})

function statusBadge(status) {
  return { draft: 'badge-neutral', sending: 'badge-warning', sent: 'badge-success', failed: 'badge-danger' }[status] || 'badge-neutral'
}

function formatRate(val) {
  return val != null ? (val * 100).toFixed(1) : '0.0'
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function openCreate() {
  editing.value = null
  form.value = { name: '', subject: '', body_html: '', canva_design_url: '', from_name: '' }
  formError.value = ''
  showForm.value = true
}

function editCampaign(c) {
  editing.value = c
  form.value = { name: c.name, subject: c.subject, body_html: c.body_html || '', canva_design_url: c.canva_design_url || '', from_name: c.from_name || '' }
  formError.value = ''
  showForm.value = true
}

async function saveCampaign() {
  if (!form.value.name || !form.value.subject) { formError.value = 'Name and subject are required.'; return }
  saving.value = true
  formError.value = ''
  try {
    if (editing.value) {
      const { data } = await campaignsApi.update(websiteId.value, editing.value.id, form.value)
      const idx = campaigns.value.findIndex(c => c.id === editing.value.id)
      if (idx >= 0) campaigns.value[idx] = data?.data || data
      toast.success('Campaign updated.')
    } else {
      const { data } = await campaignsApi.create(websiteId.value, form.value)
      campaigns.value.unshift(data?.data || data)
      toast.success('Campaign created.')
    }
    showForm.value = false
  } catch (err) {
    formError.value = err.displayMessage || 'Failed to save campaign.'
  } finally {
    saving.value = false
  }
}

async function sendCampaign(c) {
  sending.value = c.id
  try {
    await campaignsApi.send(websiteId.value, c.id)
    const idx = campaigns.value.findIndex(x => x.id === c.id)
    if (idx >= 0) campaigns.value[idx] = { ...campaigns.value[idx], status: 'sending' }
    toast.success('Campaign is being sent.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to send campaign.')
  } finally {
    sending.value = null
  }
}

async function deleteCampaign(c) {
  if (!confirm(`Delete campaign "${c.name}"?`)) return
  try {
    await campaignsApi.delete(websiteId.value, c.id)
    campaigns.value = campaigns.value.filter(x => x.id !== c.id)
    toast.success('Campaign deleted.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to delete campaign.')
  }
}

async function viewStats(c) {
  statsModal.value = c
  stats.value = null
  loadingStats.value = true
  try {
    const { data } = await campaignsApi.stats(websiteId.value, c.id)
    stats.value = data?.data || data
  } catch {
    stats.value = {}
  } finally {
    loadingStats.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await campaignsApi.list(websiteId.value)
    campaigns.value = data?.results || data || []
  } catch {
    campaigns.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: var(--font-sm); color: var(--text-muted); margin: 4px 0 0; }

.loading-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 0; color: var(--text-muted); }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 24px; text-align: center; }
.empty-icon { color: var(--text-muted); margin-bottom: 4px; }
.empty-state h3 { margin: 0; font-size: var(--font-lg); }

.campaigns-list { display: flex; flex-direction: column; gap: 16px; }

.campaign-card { padding: 20px; }
.campaign-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.campaign-name { font-weight: 600; font-size: var(--font-base); color: var(--text-primary); }
.campaign-subject { margin-top: 2px; }

.campaign-stats { display: flex; gap: 32px; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); }
.cstat { display: flex; flex-direction: column; gap: 2px; }
.cstat-val { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); }
.cstat-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

.campaign-actions { display: flex; gap: 8px; }

.badge-neutral { background: var(--bg-surface); color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }
.badge-warning { background: rgba(245,158,11,0.1); color: #b45309; border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }
.badge-success { background: rgba(16,185,129,0.1); color: #047857; border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }
.badge-danger { background: rgba(239,68,68,0.1); color: #b91c1c; border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }

.modal-overlay { position: fixed; inset: 0; z-index: 200; background: var(--bg-overlay); display: flex; align-items: center; justify-content: center; }
.modal-card { background: var(--bg-card); border-radius: var(--radius-lg); padding: 28px; max-width: 90vw; box-shadow: var(--shadow-lg); }
.form-label { display: block; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
</style>
