<template>
  <div class="llm-ranking-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">LLM Ranking</h1>
        <p class="page-subtitle">
          See how AI tools like Claude, GPT-4, Gemini, and Perplexity rank your business
          when users ask them to find a service like yours.
        </p>
      </div>
      <button class="btn btn-primary btn-sm" @click="openRunAudit" :disabled="running">
        {{ running ? 'Running audit...' : 'Run New Audit' }}
      </button>
    </div>

    <div v-if="loading" class="loading-state">Loading LLM ranking data...</div>

    <template v-else>
      <!-- Score Summary (latest audit) -->
      <div v-if="latestAudit" class="card" style="margin-bottom:24px">
        <div class="score-main">
          <div class="score-ring-wrap">
            <svg viewBox="0 0 100 100" class="score-ring-svg">
              <circle cx="50" cy="50" r="42" class="ring-track" />
              <circle cx="50" cy="50" r="42" class="ring-fill" :style="ringFillStyle(latestAudit.overall_score)" />
            </svg>
            <div class="score-center">
              <span class="score-num">{{ latestAudit.overall_score ?? '—' }}</span>
              <span class="score-denom">/100</span>
            </div>
          </div>
          <div class="score-meta">
            <div class="card-title">AI Visibility Score</div>
            <p class="text-sm text-muted" style="margin-top:4px;margin-bottom:12px">
              How prominently LLMs mention your business
            </p>
            <div class="flex gap-8">
              <span class="badge" :class="mentionBadge(latestAudit.mention_rate)">
                {{ Math.round(latestAudit.mention_rate || 0) }}% mention rate
              </span>
              <span class="badge badge-neutral">{{ (latestAudit.providers_queried || []).length }} providers queried</span>
            </div>
            <div v-if="latestAudit.status === 'running' || latestAudit.status === 'pending'" class="audit-progress-card">
              <div class="progress-header">
                <span class="pulse-dot"></span>
                <span class="progress-label">{{ latestAudit.status === 'pending' ? 'Queued — waiting to start...' : 'Audit in progress' }}</span>
                <span class="progress-pct">{{ auditProgressPct }}%</span>
              </div>
              <div class="progress-bar-track">
                <div class="progress-bar-fill" :style="{ width: auditProgressPct + '%' }"></div>
              </div>
              <div class="progress-details">
                <span>{{ latestAudit.queries_completed || 0 }} / {{ latestAudit.total_queries || '?' }} queries</span>
                <span v-if="auditETA">ETA: {{ auditETA }}</span>
                <span v-else-if="latestAudit.status === 'running'">Calculating ETA...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Provider Breakdown -->
        <div v-if="latestBreakdown.length" class="provider-grid" style="margin-top:24px">
          <div
            v-for="p in latestBreakdown"
            :key="p.provider"
            class="provider-card"
            :class="{ 'provider-mentioned': p.mentioned > 0, 'provider-failed': p.succeeded === 0 }"
          >
            <div class="provider-icon">{{ providerInitial(p.provider) }}</div>
            <div class="provider-name">{{ p.provider_display || providerLabel(p.provider) }}</div>
            <!-- Failed / unconfigured provider -->
            <template v-if="p.succeeded === 0">
              <span class="badge badge-danger">Not configured</span>
              <div class="text-xs text-muted" style="margin-top:4px">API key missing</div>
            </template>
            <!-- Queried and got results -->
            <template v-else>
              <span class="badge" :class="p.mentioned > 0 ? 'badge-success' : 'badge-neutral'">
                {{ p.mention_rate }}% mentioned
              </span>
              <div v-if="p.avg_rank" class="text-xs text-muted" style="margin-top:4px">Avg rank #{{ p.avg_rank }}</div>
              <div class="text-xs" style="margin-top:2px;color:var(--text-muted)">{{ p.succeeded }}/{{ p.total_prompts }} queries OK</div>
            </template>
          </div>
        </div>

        <!-- Score Breakdown -->
        <div v-if="latestAudit && latestAudit.status === 'completed'" class="score-breakdown" style="margin-top:16px">
          <div class="text-xs text-muted" style="line-height:1.6">
            <strong>Score breakdown:</strong>
            {{ Math.round(latestAudit.mention_rate || 0) }}% mention rate
            ({{ Math.round((latestAudit.mention_rate || 0) * 0.4) }} pts) +
            rank bonus ({{ latestAudit.avg_mention_rank ? 'avg #' + latestAudit.avg_mention_rank : 'N/A' }}) +
            sentiment + provider coverage =
            <strong>{{ latestAudit.overall_score }}/100</strong>
          </div>
        </div>
      </div>

      <!-- Detailed Findings -->
      <div v-if="auditDetail && auditDetail.results && auditDetail.results.length" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showFindings = !showFindings">
          <h3 class="card-title">Detailed Findings ({{ auditDetail.results.length }} queries)</h3>
          <span class="text-xs text-muted">{{ showFindings ? 'Hide' : 'Show' }}</span>
        </div>
        <div v-if="showFindings" class="findings-list">
          <div v-for="(r, i) in auditDetail.results" :key="i" class="finding-card" :class="{ 'finding-mentioned': r.is_mentioned, 'finding-failed': !r.query_succeeded }">
            <div class="finding-header">
              <span class="finding-provider">{{ providerLabel(r.provider) }}</span>
              <span v-if="!r.query_succeeded" class="badge badge-danger">API Failed</span>
              <span v-else-if="r.is_mentioned" class="badge badge-success">Mentioned #{{ r.mention_rank || '?' }}</span>
              <span v-else class="badge badge-neutral">Not mentioned</span>
              <span v-if="r.sentiment && r.sentiment !== 'not_mentioned'" class="badge" :class="r.sentiment === 'positive' ? 'badge-success' : r.sentiment === 'negative' ? 'badge-danger' : 'badge-neutral'" style="margin-left:4px">
                {{ r.sentiment }}
              </span>
            </div>
            <div class="finding-prompt">
              <span class="finding-label">Prompt:</span> {{ r.prompt }}
            </div>
            <div v-if="r.mention_context" class="finding-context">
              <span class="finding-label">Found in:</span> "{{ r.mention_context }}"
            </div>
            <div v-if="r.error_message" class="finding-error">
              <span class="finding-label">Error:</span> {{ r.error_message }}
            </div>
            <details v-if="r.response_text" class="finding-response">
              <summary class="text-xs text-muted" style="cursor:pointer">View full LLM response</summary>
              <pre class="response-pre">{{ r.response_text }}</pre>
            </details>
          </div>
        </div>
      </div>

      <!-- Recommendations -->
      <div v-if="recommendations.length" class="card" style="margin-bottom:24px">
        <div class="card-header">
          <h3 class="card-title">Recommendations</h3>
        </div>
        <div class="recs-list">
          <div v-for="(rec, i) in recommendations" :key="i" class="rec-row">
            <span class="rec-num">{{ i + 1 }}</span>
            <span class="text-sm" style="color:var(--text-secondary);line-height:1.5">{{ rec }}</span>
          </div>
        </div>
      </div>

      <!-- Audit History -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Audit History</h3>
        </div>

        <div v-if="audits.length === 0" class="empty-state">
          <div class="empty-state-title">No audits yet</div>
          <p class="empty-state-desc">Run your first audit to see how LLMs rank your business.</p>
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
            <tr
              v-for="audit in audits"
              :key="audit.id"
              class="audit-row"
              :class="{ 'row-selected': selectedAuditId === audit.id }"
              @click="selectAudit(audit)"
            >
              <td class="text-sm">{{ formatDate(audit.created_at) }}</td>
              <td class="font-semibold">{{ audit.business_name }}</td>
              <td>
                <span class="score-pill" :class="scorePillClass(audit.overall_score)">
                  {{ audit.overall_score ?? '—' }}
                </span>
              </td>
              <td class="text-sm">{{ Math.round(audit.mention_rate || 0) }}%</td>
              <td><span class="badge" :class="auditStatusBadge(audit.status)">{{ audit.status }}</span></td>
              <td>
                <!-- Inline delete confirmation -->
                <div v-if="confirmDeleteId === audit.id" class="flex gap-8 items-center">
                  <span class="text-xs" style="color:var(--color-danger)">Delete?</span>
                  <button class="btn btn-danger btn-sm" @click.stop="confirmDelete(audit)">Yes</button>
                  <button class="btn btn-secondary btn-sm" @click.stop="confirmDeleteId = null">No</button>
                </div>
                <button
                  v-else
                  class="btn btn-ghost btn-sm delete-btn"
                  @click.stop="confirmDeleteId = audit.id"
                >Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Run Audit Modal -->
    <div v-if="showRunForm" class="modal-overlay" @click.self="showRunForm = false">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title">Run LLM Ranking Audit</div>
          <button class="btn btn-ghost btn-icon" @click="showRunForm = false">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><line x1="2" y1="2" x2="14" y2="14"/><line x1="14" y1="2" x2="2" y2="14"/></svg>
          </button>
        </div>
        <div class="form-group">
          <label class="form-label">Business Name</label>
          <input v-model="auditForm.business_name" class="form-input" placeholder="e.g. Acme Corp" />
        </div>
        <div class="form-group" style="margin-top:12px">
          <label class="form-label">Industry / Category</label>
          <input v-model="auditForm.industry" class="form-input" placeholder="e.g. SaaS, e-commerce, marketing agency" />
        </div>
        <div class="form-group" style="margin-top:12px">
          <label class="form-label">Location (optional)</label>
          <input v-model="auditForm.location" class="form-input" placeholder="e.g. New York, US" />
        </div>
        <div class="form-group" style="margin-top:12px">
          <label class="form-label">Custom Prompts (optional, one per line)</label>
          <textarea v-model="customPromptsText" class="form-input" rows="3" placeholder="Best SaaS tools for startups"></textarea>
          <p class="text-xs text-muted" style="margin-top:4px">Leave blank to use auto-generated prompts.</p>
        </div>
        <div class="form-group" style="margin-top:12px">
          <label class="form-label">Providers</label>
          <div class="provider-checks">
            <label v-for="p in availableProviders" :key="p.value" class="check-label">
              <input type="checkbox" :value="p.value" v-model="auditForm.providers" />
              {{ p.label }}
            </label>
          </div>
        </div>
        <p v-if="auditError" class="form-error" style="margin-top:8px">{{ auditError }}</p>
        <div class="flex gap-8" style="justify-content:flex-end;margin-top:20px">
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import llmRankingApi from '@/api/llm_ranking'

const route = useRoute()
const websiteId = route.params.websiteId
const toast = useToast()

const audits = ref([])
const loading = ref(true)
const running = ref(false)
const showRunForm = ref(false)
const auditError = ref('')
const selectedAuditId = ref(null)
const latestBreakdown = ref([])
const recommendations = ref([])
const auditDetail = ref(null)
const showFindings = ref(true)
const confirmDeleteId = ref(null)
let pollTimer = null

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

const auditProgressPct = computed(() => {
  const a = latestAudit.value
  if (!a || !a.total_queries) return 0
  return Math.min(100, Math.round((a.queries_completed / a.total_queries) * 100))
})

const auditETA = computed(() => {
  const a = latestAudit.value
  if (!a || !a.started_at || !a.queries_completed || !a.total_queries) return ''
  const started = new Date(a.started_at).getTime()
  const now = Date.now()
  const elapsed = (now - started) / 1000 // seconds
  const perQuery = elapsed / a.queries_completed
  const remaining = (a.total_queries - a.queries_completed) * perQuery
  if (remaining < 5) return 'Almost done...'
  if (remaining < 60) return `~${Math.ceil(remaining)}s remaining`
  const mins = Math.ceil(remaining / 60)
  return `~${mins} min remaining`
})

function ringFillStyle(score) {
  if (score == null) return {}
  const pct = Math.min(100, Math.max(0, score))
  const circ = 2 * Math.PI * 42
  const stroke = pct >= 70
    ? 'var(--color-success)'
    : pct >= 40
      ? 'var(--color-warning)'
      : 'var(--color-danger)'
  return {
    strokeDasharray: `${(pct / 100) * circ} ${circ}`,
    stroke,
  }
}

function mentionBadge(rate) {
  // mention_rate is already 0-100 from backend
  const pct = rate || 0
  return pct >= 60 ? 'badge-success' : pct >= 30 ? 'badge-warning' : 'badge-neutral'
}

function providerLabel(p) {
  return { claude: 'Claude', gpt4: 'GPT-4', gemini: 'Gemini', perplexity: 'Perplexity' }[p] || p
}

function providerInitial(p) {
  return { claude: 'A', gpt4: 'G', gemini: 'G', perplexity: 'P' }[p] || p[0].toUpperCase()
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function scorePillClass(score) {
  if (score == null) return 'pill-neutral'
  return score >= 70 ? 'pill-green' : score >= 40 ? 'pill-yellow' : 'pill-red'
}

function auditStatusBadge(status) {
  return {
    pending: 'badge-neutral',
    running: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
  }[status] || 'badge-neutral'
}

function openRunAudit() {
  auditError.value = ''
  customPromptsText.value = ''
  auditForm.value = { business_name: '', industry: '', location: '', providers: ['claude', 'gpt4', 'gemini', 'perplexity'] }
  showRunForm.value = true
}

async function submitAudit() {
  if (!auditForm.value.business_name) { auditError.value = 'Business name is required.'; return }
  if (!auditForm.value.industry) { auditError.value = 'Industry is required.'; return }
  if (!auditForm.value.providers.length) { auditError.value = 'Select at least one provider.'; return }
  running.value = true
  auditError.value = ''
  try {
    const payload = {
      business_name: auditForm.value.business_name,
      industry: auditForm.value.industry,
      location: auditForm.value.location,
      providers: auditForm.value.providers,
    }
    if (customPromptsText.value.trim()) {
      payload.custom_prompts = customPromptsText.value.split('\n').map(s => s.trim()).filter(Boolean)
    }
    const { data } = await llmRankingApi.runAudit(websiteId, payload)
    const audit = data?.data || data
    audits.value.unshift(audit)
    selectedAuditId.value = audit.id
    showRunForm.value = false
    toast.success('Audit queued. Results will appear once complete.')
    // Start polling for results
    startPolling()
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
  auditDetail.value = null

  if (audit.status !== 'completed') return

  try {
    const [bRes, rRes, dRes] = await Promise.all([
      llmRankingApi.breakdown(websiteId, audit.id),
      llmRankingApi.recommendations(websiteId, audit.id),
      llmRankingApi.getAudit(websiteId, audit.id),
    ])
    latestBreakdown.value = bRes.data?.data || bRes.data?.results || bRes.data || []
    recommendations.value = rRes.data?.data?.recommendations || rRes.data?.recommendations || []
    auditDetail.value = dRes.data?.data || dRes.data || null
  } catch (e) {
    console.error('Audit breakdown fetch error', e)
  }
}

async function confirmDelete(audit) {
  confirmDeleteId.value = null
  try {
    await llmRankingApi.deleteAudit(websiteId, audit.id)
    audits.value = audits.value.filter(a => a.id !== audit.id)
    if (selectedAuditId.value === audit.id) {
      selectedAuditId.value = null
      latestBreakdown.value = []
      recommendations.value = []
    }
    toast.success('Audit deleted.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to delete audit.')
  }
}

// Auto-polling for running audits
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    const hasRunning = audits.value.some(a => a.status === 'pending' || a.status === 'running')
    if (!hasRunning) {
      stopPolling()
      return
    }
    try {
      const { data } = await llmRankingApi.listAudits(websiteId)
      const newAudits = data?.data?.results || data?.results || data || []
      // Check if any previously running audit has completed
      for (const newA of newAudits) {
        const oldA = audits.value.find(a => a.id === newA.id)
        if (oldA && (oldA.status === 'pending' || oldA.status === 'running') && newA.status === 'completed') {
          toast.success(`Audit for "${newA.business_name}" completed! Score: ${newA.overall_score}/100`)
        }
      }
      audits.value = newAudits
      // Load breakdown for the latest completed audit
      if (audits.value.length && audits.value[0].status === 'completed' && !latestBreakdown.value.length) {
        await selectAudit(audits.value[0])
      }
    } catch (e) {
      console.error('Poll error', e)
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function fetchData() {
  loading.value = true
  try {
    const { data } = await llmRankingApi.listAudits(websiteId)
    audits.value = data?.data?.results || data?.results || data || []
    if (audits.value.length) {
      // Auto-select the first completed audit so its findings load
      const firstCompleted = audits.value.find(a => a.status === 'completed')
      if (firstCompleted) {
        selectedAuditId.value = firstCompleted.id
        await selectAudit(firstCompleted)
      } else {
        selectedAuditId.value = audits.value[0].id
      }
      // Start polling if any audits are running
      if (audits.value.some(a => a.status === 'pending' || a.status === 'running')) {
        startPolling()
      }
    }
  } catch (e) {
    console.error('LLM ranking fetch error', e)
    audits.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* Score summary */
.score-main { display: flex; align-items: center; gap: 32px; }
.score-ring-wrap { position: relative; width: 110px; height: 110px; flex-shrink: 0; }
.score-ring-svg { width: 110px; height: 110px; transform: rotate(-90deg); }
.ring-track { fill: none; stroke: var(--border-color); stroke-width: 8; }
.ring-fill { fill: none; stroke-width: 8; stroke-linecap: round; transition: stroke-dasharray 0.6s ease; }
.score-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-num { font-size: 26px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.score-denom { font-size: var(--font-xs); color: var(--text-muted); }
.score-meta { flex: 1; }

/* Running audit progress */
.audit-progress-card {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
}
.progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.progress-label {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.progress-pct {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--color-warning);
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-warning);
  animation: pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
.progress-bar-track {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-warning), var(--color-success));
  border-radius: 3px;
  transition: width 0.5s ease;
  min-width: 2px;
}
.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: var(--font-xs);
  color: var(--text-muted);
}

/* Provider grid */
.provider-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.provider-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  transition: border-color var(--transition-fast);
}
.provider-card.provider-mentioned { border-color: var(--color-success); background: var(--color-success-bg); }
.provider-card.provider-failed { opacity: 0.5; border-style: dashed; }
.score-breakdown { padding: 12px 16px; border-radius: var(--radius-md); background: var(--bg-surface); border: 1px solid var(--border-color); }
.provider-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: var(--font-base);
  color: var(--text-secondary);
}
.provider-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }

/* Detailed Findings */
.findings-list { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.finding-card {
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--text-muted);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  background: var(--bg-base);
}
.finding-card.finding-mentioned { border-left-color: var(--color-success); }
.finding-card.finding-failed { border-left-color: var(--color-danger); opacity: 0.6; }
.finding-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.finding-provider { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); }
.finding-label { font-weight: 600; color: var(--text-muted); font-size: var(--font-xs); text-transform: uppercase; letter-spacing: 0.5px; }
.finding-prompt { font-size: var(--font-sm); color: var(--text-secondary); margin-bottom: 6px; line-height: 1.5; }
.finding-context { font-size: var(--font-sm); color: var(--color-success); font-style: italic; margin-bottom: 6px; }
.finding-error { font-size: var(--font-xs); color: var(--color-danger); margin-bottom: 6px; }
.finding-response { margin-top: 8px; }
.response-pre {
  margin-top: 8px;
  padding: 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  font-size: var(--font-xs);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

/* Recommendations */
.recs-list { display: flex; flex-direction: column; gap: 0; }
.rec-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}
.rec-row:last-child { border-bottom: none; }
.rec-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--text-primary);
  color: var(--text-inverse);
  font-size: var(--font-xs);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Audit table */
.audit-row { cursor: pointer; }
.audit-row.row-selected td { background: var(--bg-surface); }

.score-pill { padding: 2px 10px; border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 700; }
.pill-green { background: var(--color-success-bg); color: var(--color-success); }
.pill-yellow { background: var(--color-warning-bg); color: var(--color-warning); }
.pill-red { background: var(--color-danger-bg); color: var(--color-danger); }
.pill-neutral { background: var(--bg-surface); color: var(--text-muted); }

.delete-btn { color: var(--color-danger); }

/* Modal extras */
.provider-checks { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 4px; }
.check-label { display: flex; align-items: center; gap: 6px; font-size: var(--font-sm); color: var(--text-secondary); cursor: pointer; }
</style>
