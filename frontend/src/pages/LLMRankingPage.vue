<template>
  <div class="llm-ranking-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">LLM Ranking</h1>
        <p class="page-subtitle">See how AI tools like Claude, GPT-4, Gemini, and Perplexity rank your business when users ask them to find a service like yours.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="openRunAudit" :disabled="running">
        <svg v-if="!running" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:-2px;margin-right:6px"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        {{ running ? 'Running audit...' : 'Run New Audit' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading LLM ranking data...</p>
    </div>

    <template v-else>
      <!-- Score Summary (latest audit) -->
      <div v-if="latestAudit" class="score-summary card" style="margin-bottom:24px">
        <div class="score-main">
          <div class="score-ring-wrap">
            <svg viewBox="0 0 100 100" class="score-ring-svg">
              <circle cx="50" cy="50" r="42" class="ring-bg" />
              <circle cx="50" cy="50" r="42" class="ring-fill" :style="ringStyle(latestAudit.overall_score)" />
            </svg>
            <div class="score-center">
              <span class="score-num">{{ latestAudit.overall_score ?? '—' }}</span>
              <span class="score-denom">/100</span>
            </div>
          </div>
          <div class="score-meta">
            <div class="score-title">AI Visibility Score</div>
            <div class="score-desc text-muted text-sm">How prominently LLMs mention your business</div>
            <div class="score-chips">
              <span class="chip" :class="mentionChip(latestAudit.mention_rate)">{{ Math.round((latestAudit.mention_rate || 0) * 100) }}% mention rate</span>
              <span class="chip chip-neutral">{{ latestAudit.providers_queried || 0 }} providers queried</span>
            </div>
          </div>
        </div>

        <!-- Provider Breakdown -->
        <div v-if="latestBreakdown.length" class="provider-grid">
          <div v-for="p in latestBreakdown" :key="p.provider" class="provider-card" :class="{ 'provider-mentioned': p.is_mentioned }">
            <div class="provider-name">{{ providerLabel(p.provider) }}</div>
            <div class="provider-icon">{{ providerIcon(p.provider) }}</div>
            <div class="provider-status">
              <span v-if="p.is_mentioned" class="chip chip-success">Mentioned</span>
              <span v-else class="chip chip-muted">Not mentioned</span>
            </div>
            <div v-if="p.mention_rank" class="provider-rank text-sm text-muted">Rank #{{ p.mention_rank }}</div>
            <div class="provider-sentiment text-xs" :class="sentimentClass(p.sentiment)">{{ p.sentiment }}</div>
          </div>
        </div>
      </div>

      <!-- Recommendations -->
      <div v-if="recommendations.length" class="card" style="margin-bottom:24px">
        <div class="card-header-row">
          <h3 class="section-title" style="margin:0">Recommendations</h3>
        </div>
        <div class="recs-list">
          <div v-for="(rec, i) in recommendations" :key="i" class="rec-row">
            <span class="rec-num">{{ i + 1 }}</span>
            <span class="rec-text">{{ rec }}</span>
          </div>
        </div>
      </div>

      <!-- Audit History -->
      <div class="card">
        <h3 class="section-title">Audit History</h3>
        <div v-if="audits.length === 0" class="empty-inline text-muted text-sm" style="padding:24px 0;text-align:center">
          No audits yet. Run your first audit to see how LLMs rank your business.
        </div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Business</th>
              <th>Score</th>
              <th>Mention Rate</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="audit in audits" :key="audit.id" @click="selectAudit(audit)" style="cursor:pointer" :class="{ 'row-active': selectedAuditId === audit.id }">
              <td class="text-sm">{{ formatDate(audit.created_at) }}</td>
              <td class="font-medium">{{ audit.business_name }}</td>
              <td>
                <span class="score-pill" :class="scorePillClass(audit.overall_score)">{{ audit.overall_score ?? '—' }}</span>
              </td>
              <td class="text-sm">{{ Math.round((audit.mention_rate || 0) * 100) }}%</td>
              <td><span class="badge" :class="auditStatusBadge(audit.status)">{{ audit.status }}</span></td>
              <td>
                <button class="btn btn-ghost btn-xs" style="color:var(--color-danger)" @click.stop="deleteAudit(audit)">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Run Audit Modal -->
    <div v-if="showRunForm" class="modal-overlay" @click.self="showRunForm = false">
      <div class="modal-card" style="width:480px">
        <h3 class="card-title" style="margin-bottom:20px">Run LLM Ranking Audit</h3>
        <div style="margin-bottom:12px">
          <label class="form-label">Business Name</label>
          <input v-model="auditForm.business_name" class="form-input" placeholder="e.g. Acme Corp" />
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Industry / Category</label>
          <input v-model="auditForm.industry" class="form-input" placeholder="e.g. SaaS, e-commerce, marketing agency" />
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Location (optional)</label>
          <input v-model="auditForm.location" class="form-input" placeholder="e.g. New York, US" />
        </div>
        <div style="margin-bottom:12px">
          <label class="form-label">Custom Prompts (optional, one per line)</label>
          <textarea v-model="customPromptsText" class="form-input" rows="3" placeholder="Best SaaS tools for startups&#10;Top marketing software 2024"></textarea>
          <p class="text-xs text-muted" style="margin-top:4px">Leave blank to use auto-generated prompts.</p>
        </div>
        <div style="margin-bottom:20px">
          <label class="form-label">Providers</label>
          <div class="provider-checks">
            <label v-for="p in availableProviders" :key="p.value" class="check-label">
              <input type="checkbox" :value="p.value" v-model="auditForm.providers" />
              {{ p.label }}
            </label>
          </div>
        </div>
        <p v-if="auditError" class="text-sm" style="color:var(--color-danger);margin-bottom:12px">{{ auditError }}</p>
        <div class="flex gap-8" style="justify-content:flex-end">
          <button class="btn btn-secondary" @click="showRunForm = false">Cancel</button>
          <button class="btn btn-primary" @click="submitAudit" :disabled="running">
            {{ running ? 'Queuing...' : 'Start Audit' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import llmRankingApi from '@/api/llm_ranking'

const props = defineProps({ websiteId: String })
const route = useRoute()
const toast = useToast()

const websiteId = computed(() => props.websiteId || route.params.websiteId)

const audits = ref([])
const loading = ref(true)
const running = ref(false)
const showRunForm = ref(false)
const auditError = ref('')
const selectedAuditId = ref(null)
const latestBreakdown = ref([])
const recommendations = ref([])

const customPromptsText = ref('')
const auditForm = ref({
  business_name: '',
  industry: '',
  location: '',
  providers: ['claude', 'gpt4', 'gemini', 'perplexity'],
})

const availableProviders = [
  { value: 'claude', label: 'Claude (Anthropic)' },
  { value: 'gpt4', label: 'GPT-4 (OpenAI)' },
  { value: 'gemini', label: 'Gemini (Google)' },
  { value: 'perplexity', label: 'Perplexity' },
]

const latestAudit = computed(() => audits.value[0] || null)

function ringStyle(score) {
  if (score == null) return {}
  const pct = Math.min(100, Math.max(0, score))
  const circ = 2 * Math.PI * 42
  return {
    strokeDasharray: `${(pct / 100) * circ} ${circ}`,
    stroke: pct >= 70 ? 'var(--color-success, #10b981)' : pct >= 40 ? '#f59e0b' : 'var(--color-danger, #ef4444)',
  }
}

function mentionChip(rate) {
  const pct = (rate || 0) * 100
  return pct >= 60 ? 'chip-success' : pct >= 30 ? 'chip-warning' : 'chip-muted'
}

function providerLabel(p) {
  return { claude: 'Claude', gpt4: 'GPT-4', gemini: 'Gemini', perplexity: 'Perplexity' }[p] || p
}

function providerIcon(p) {
  return { claude: 'A', gpt4: 'G', gemini: 'G', perplexity: 'P' }[p] || p[0].toUpperCase()
}

function sentimentClass(s) {
  return { positive: 'text-success', neutral: 'text-muted', negative: 'text-danger' }[s] || 'text-muted'
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function scorePillClass(score) {
  if (score == null) return 'pill-neutral'
  return score >= 70 ? 'pill-green' : score >= 40 ? 'pill-yellow' : 'pill-red'
}

function auditStatusBadge(status) {
  return { pending: 'badge-neutral', running: 'badge-warning', completed: 'badge-success', failed: 'badge-danger' }[status] || 'badge-neutral'
}

function openRunAudit() {
  auditError.value = ''
  customPromptsText.value = ''
  auditForm.value = { business_name: '', industry: '', location: '', providers: ['claude', 'gpt4', 'gemini', 'perplexity'] }
  showRunForm.value = true
}

async function submitAudit() {
  if (!auditForm.value.business_name) { auditError.value = 'Business name is required.'; return }
  running.value = true
  auditError.value = ''
  try {
    const payload = { ...auditForm.value }
    if (customPromptsText.value.trim()) {
      payload.custom_prompts = customPromptsText.value.split('\n').map(s => s.trim()).filter(Boolean)
    }
    const { data } = await llmRankingApi.runAudit(websiteId.value, payload)
    const audit = data?.data || data
    audits.value.unshift(audit)
    selectedAuditId.value = audit.id
    showRunForm.value = false
    toast.success('Audit queued. Results will appear once complete.')
  } catch (err) {
    auditError.value = err.displayMessage || 'Failed to start audit.'
  } finally {
    running.value = false
  }
}

async function selectAudit(audit) {
  selectedAuditId.value = audit.id
  latestBreakdown.value = []
  recommendations.value = []
  try {
    const [bRes, rRes] = await Promise.all([
      llmRankingApi.breakdown(websiteId.value, audit.id),
      llmRankingApi.recommendations(websiteId.value, audit.id),
    ])
    latestBreakdown.value = bRes.data?.results || bRes.data || []
    recommendations.value = rRes.data?.recommendations || rRes.data || []
  } catch {}
}

async function deleteAudit(audit) {
  if (!confirm('Delete this audit?')) return
  try {
    await llmRankingApi.deleteAudit(websiteId.value, audit.id)
    audits.value = audits.value.filter(a => a.id !== audit.id)
    if (selectedAuditId.value === audit.id) { selectedAuditId.value = null; latestBreakdown.value = []; recommendations.value = [] }
    toast.success('Audit deleted.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to delete audit.')
  }
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await llmRankingApi.listAudits(websiteId.value)
    audits.value = data?.results || data || []
    if (audits.value.length) {
      selectedAuditId.value = audits.value[0].id
      await selectAudit(audits.value[0])
    }
  } catch {
    audits.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.page-title { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); margin: 0; }
.page-subtitle { font-size: var(--font-sm); color: var(--text-muted); margin: 4px 0 0; max-width: 560px; }

.loading-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 0; color: var(--text-muted); }

/* Score Card */
.score-summary { padding: 24px; }
.score-main { display: flex; align-items: center; gap: 32px; margin-bottom: 24px; }
.score-ring-wrap { position: relative; width: 110px; height: 110px; flex-shrink: 0; }
.score-ring-svg { width: 110px; height: 110px; transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: var(--border-color); stroke-width: 8; }
.ring-fill { fill: none; stroke-width: 8; stroke-linecap: round; transition: stroke-dasharray 0.6s ease; }
.score-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-num { font-size: 26px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.score-denom { font-size: var(--font-xs); color: var(--text-muted); }
.score-title { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.score-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }

/* Provider Grid */
.provider-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.provider-card { border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; display: flex; flex-direction: column; align-items: center; gap: 6px; text-align: center; transition: border-color 0.2s; }
.provider-card.provider-mentioned { border-color: var(--color-success, #10b981); background: rgba(16,185,129,0.04); }
.provider-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.provider-icon { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-surface); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: var(--font-base); color: var(--text-secondary); }
.provider-rank { margin-top: 2px; }

/* Chips */
.chip { display: inline-flex; align-items: center; font-size: var(--font-xs); font-weight: 600; padding: 3px 10px; border-radius: var(--radius-full); }
.chip-success { background: rgba(16,185,129,0.1); color: #047857; }
.chip-warning { background: rgba(245,158,11,0.1); color: #b45309; }
.chip-muted { background: var(--bg-surface); color: var(--text-muted); border: 1px solid var(--border-color); }
.chip-neutral { background: var(--bg-surface); color: var(--text-secondary); border: 1px solid var(--border-color); }

/* Recommendations */
.card-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.section-title { font-size: var(--font-md); font-weight: 700; color: var(--text-primary); margin-bottom: 16px; }
.recs-list { display: flex; flex-direction: column; gap: 10px; }
.rec-row { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.rec-row:last-child { border-bottom: none; }
.rec-num { width: 24px; height: 24px; border-radius: 50%; background: var(--brand-primary, #6366f1); color: #fff; font-size: var(--font-xs); font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rec-text { font-size: var(--font-sm); color: var(--text-secondary); line-height: 1.5; }

/* Table */
.data-table { width: 100%; border-collapse: collapse; font-size: var(--font-sm); }
.data-table th { text-align: left; padding: 8px 12px; font-size: var(--font-xs); font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-color); }
.data-table td { padding: 12px; border-bottom: 1px solid var(--border-color); color: var(--text-secondary); }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: var(--bg-surface); }
.data-table tr.row-active td { background: rgba(99,102,241,0.06); }

.score-pill { padding: 2px 10px; border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 700; }
.pill-green { background: rgba(16,185,129,0.1); color: #047857; }
.pill-yellow { background: rgba(245,158,11,0.1); color: #b45309; }
.pill-red { background: rgba(239,68,68,0.1); color: #b91c1c; }
.pill-neutral { background: var(--bg-surface); color: var(--text-muted); }

.badge-neutral { background: var(--bg-surface); color: var(--text-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }
.badge-warning { background: rgba(245,158,11,0.1); color: #b45309; border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }
.badge-success { background: rgba(16,185,129,0.1); color: #047857; border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }
.badge-danger { background: rgba(239,68,68,0.1); color: #b91c1c; border-radius: var(--radius-sm); padding: 2px 8px; font-size: var(--font-xs); font-weight: 600; }

.text-success { color: #047857; }
.text-danger { color: #b91c1c; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; z-index: 200; background: var(--bg-overlay); display: flex; align-items: center; justify-content: center; }
.modal-card { background: var(--bg-card); border-radius: var(--radius-lg); padding: 28px; max-width: 90vw; box-shadow: var(--shadow-lg); }
.form-label { display: block; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.provider-checks { display: flex; flex-wrap: wrap; gap: 12px; }
.check-label { display: flex; align-items: center; gap: 6px; font-size: var(--font-sm); color: var(--text-secondary); cursor: pointer; }
</style>
