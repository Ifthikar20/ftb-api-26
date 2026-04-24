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
      <div class="header-actions">
        <button class="btn btn-secondary btn-sm" @click="showScheduleModal = true">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-right:4px"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>
          {{ schedule ? 'Edit Schedule' : 'Schedule' }}
        </button>
        <button class="btn btn-primary btn-sm" @click="openRunAudit" :disabled="running">
          {{ running ? 'Running audit...' : 'Run New Audit' }}
        </button>
      </div>
    </div>

    <!-- Schedule banner -->
    <div v-if="schedule && schedule.is_enabled" class="schedule-banner">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>
      <span>Auto-audit runs <strong>{{ schedule.frequency_display }}</strong> — next run {{ formatRelative(schedule.next_run_at) }}</span>
      <button class="btn btn-ghost btn-xs" @click="disableSchedule">Disable</button>
    </div>

    <div v-if="loading" class="loading-state">Loading LLM ranking data...</div>

    <template v-else>
      <!-- How Scoring Works -->
      <div v-if="!latestAudit || latestAudit.status !== 'completed'" class="card methodology-card" style="margin-bottom:24px">
        <div class="card-header">
          <h3 class="card-title">How LLM Ranking Works</h3>
        </div>
        <div class="methodology-content">
          <p class="text-sm text-muted" style="margin-bottom:16px;line-height:1.6">
            We ask leading AI assistants natural questions about your industry and analyze their responses
            to measure how visible your business is in AI-generated answers. The audit scores three factors:
          </p>
          <div class="method-grid">
            <div class="method-item">
              <div class="method-weight">40 pts</div>
              <div class="method-title">Mention Rate</div>
              <div class="method-desc">How often your business appears in AI responses across all prompts</div>
            </div>
            <div class="method-item">
              <div class="method-weight">35 pts</div>
              <div class="method-title">Rank Position</div>
              <div class="method-desc">Where you appear in ranked lists — #1 scores highest, lower positions score less</div>
            </div>
            <div class="method-item">
              <div class="method-weight">25 pts</div>
              <div class="method-title">Sentiment + Coverage</div>
              <div class="method-desc">Whether mentions are positive/neutral and how many providers include you</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Score Summary (latest completed audit) -->
      <div v-if="latestAudit" class="card" style="margin-bottom:24px">
        <div class="score-main">
          <div class="score-ring-wrap">
            <svg viewBox="0 0 100 100" class="score-ring-svg">
              <circle cx="50" cy="50" r="42" class="ring-track" />
              <circle cx="50" cy="50" r="42" class="ring-fill" :style="ringFillStyle(latestAudit.overall_score)" />
            </svg>
            <div class="score-center">
              <span class="score-num">{{ isAuditComplete ? latestAudit.overall_score : '—' }}</span>
              <span class="score-denom">/100</span>
            </div>
          </div>
          <div class="score-meta">
            <div class="card-title">AI Visibility Score</div>
            <p class="text-sm text-muted" style="margin-top:4px;margin-bottom:12px">
              {{ isAuditComplete
                ? 'How prominently LLMs mention your business'
                : 'Score will appear once the audit finishes running.' }}
            </p>
            <div class="flex gap-8" style="margin-bottom:8px">
              <span v-if="isAuditComplete" class="badge" :class="mentionBadge(latestAudit.mention_rate)">
                {{ Math.round(latestAudit.mention_rate || 0) }}% mention rate
              </span>
              <span v-else class="badge badge-neutral">Running across {{ (latestAudit.providers_queried || []).length }} provider{{ (latestAudit.providers_queried || []).length !== 1 ? 's' : '' }}</span>
              <span v-if="isAuditComplete" class="badge badge-neutral">{{ (latestAudit.providers_queried || []).length }} provider{{ (latestAudit.providers_queried || []).length !== 1 ? 's' : '' }}</span>
              <span v-if="latestAudit.location" class="badge badge-neutral">{{ latestAudit.location }}</span>
            </div>
            <!-- Progress bar for running audits -->
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

        <!-- Visual Score Breakdown -->
        <div v-if="latestAudit.status === 'completed'" class="score-factors" style="margin-top:20px">
          <h4 class="text-sm font-semibold" style="margin-bottom:12px;color:var(--text-primary)">Score Breakdown</h4>
          <div class="factor-row">
            <span class="factor-label">Mention Rate (40pts)</span>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: mentionPts + '%', background: mentionPts > 25 ? 'var(--color-success)' : mentionPts > 10 ? 'var(--color-warning)' : 'var(--color-danger)' }"></div>
            </div>
            <span class="factor-value">{{ mentionPts }}/40</span>
          </div>
          <div class="factor-row">
            <span class="factor-label">Rank Position (35pts)</span>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: rankPts / 35 * 100 + '%', background: rankPts > 20 ? 'var(--color-success)' : rankPts > 10 ? 'var(--color-warning)' : 'var(--color-danger)' }"></div>
            </div>
            <span class="factor-value">{{ rankPts }}/35</span>
          </div>
          <div class="factor-row">
            <span class="factor-label">Sentiment + Coverage (25pts)</span>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: sentimentPts / 25 * 100 + '%', background: sentimentPts > 15 ? 'var(--color-success)' : sentimentPts > 8 ? 'var(--color-warning)' : 'var(--color-danger)' }"></div>
            </div>
            <span class="factor-value">{{ sentimentPts }}/25</span>
          </div>
          <div class="factor-total">
            <span>Total Score</span>
            <span class="font-semibold">{{ latestAudit.overall_score }}/100</span>
          </div>
        </div>

        <!-- Provider Breakdown -->
        <div v-if="latestBreakdown.length" class="provider-grid" style="margin-top:20px">
          <div
            v-for="p in latestBreakdown"
            :key="p.provider"
            class="provider-card"
            :class="{ 'provider-mentioned': p.mentioned > 0, 'provider-failed': p.succeeded === 0 }"
          >
            <div class="provider-icon">{{ providerInitial(p.provider) }}</div>
            <div class="provider-name">{{ p.provider_display || providerLabel(p.provider) }}</div>
            <template v-if="p.succeeded === 0">
              <span class="badge badge-danger">Not configured</span>
              <div class="text-xs text-muted" style="margin-top:4px">API key missing</div>
            </template>
            <template v-else>
              <span class="badge" :class="p.mentioned > 0 ? 'badge-success' : 'badge-neutral'">
                {{ p.mention_rate }}% mentioned
              </span>
              <div v-if="p.avg_rank" class="text-xs text-muted" style="margin-top:4px">Avg rank #{{ p.avg_rank }}</div>
              <div class="text-xs" style="margin-top:2px;color:var(--text-muted)">{{ p.succeeded }}/{{ p.total_prompts }} queries OK</div>
            </template>
          </div>
        </div>
      </div>

      <!-- ═══ Charts Section ═══ -->
      <div v-if="latestBreakdown.length || historyData.length" class="charts-row" style="margin-bottom:24px">
        <!-- Provider Comparison Bar Chart -->
        <div v-if="latestBreakdown.length" class="card chart-card">
          <div class="card-header">
            <h3 class="card-title">Provider Comparison</h3>
            <span class="text-xs text-muted">Mention rate across LLMs</span>
          </div>
          <div class="chart-wrap">
            <Bar :data="providerChartData" :options="providerChartOptions" />
          </div>
        </div>

        <!-- Trend Line Chart -->
        <div v-if="historyData.length >= 2" class="card chart-card">
          <div class="card-header">
            <h3 class="card-title">Score Trend</h3>
            <span class="text-xs text-muted">AI visibility over time</span>
          </div>
          <div class="chart-wrap">
            <Line :data="trendChartData" :options="trendChartOptions" />
          </div>
        </div>
      </div>

      <!-- Detailed Findings -->
      <div v-if="auditDetail && auditDetail.results && auditDetail.results.length" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showFindings = !showFindings">
          <h3 class="card-title">Detailed Findings ({{ successfulResults.length }} queries analyzed)</h3>
          <span class="text-xs text-muted">{{ showFindings ? 'Collapse' : 'Expand' }}</span>
        </div>
        <div v-if="showFindings" class="findings-list">
          <!-- Summary stats at top -->
          <div class="findings-summary">
            <div class="summary-stat">
              <span class="summary-num">{{ successfulResults.length }}</span>
              <span class="summary-label">Queries Sent</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ mentionedResults.length }}</span>
              <span class="summary-label">Mentions Found</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ mentionedResults.length ? avgRankDisplay : 'N/A' }}</span>
              <span class="summary-label">Avg Rank</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ promptsUsed }}</span>
              <span class="summary-label">Unique Prompts</span>
            </div>
          </div>

          <!-- Per-query results -->
          <template v-for="(r, i) in auditDetail.results" :key="i">
            <div v-if="r.query_succeeded" class="finding-card" :class="{ 'finding-mentioned': r.is_mentioned }">
              <div class="finding-number">#{{ i + 1 }}</div>
              <div class="finding-body">
                <div class="finding-header">
                  <span class="finding-provider">{{ providerLabel(r.provider) }}</span>
                  <span v-if="r.is_mentioned" class="badge badge-success">Ranked #{{ r.mention_rank || '?' }}</span>
                  <span v-else class="badge badge-neutral">Not found in response</span>
                  <span v-if="r.sentiment && r.sentiment !== 'not_mentioned'" class="badge" :class="r.sentiment === 'positive' ? 'badge-success' : r.sentiment === 'negative' ? 'badge-danger' : 'badge-neutral'" style="margin-left:4px">
                    {{ r.sentiment }}
                  </span>
                  <span class="finding-confidence" v-if="r.confidence_score">{{ Math.round(r.confidence_score) }}% confidence</span>
                </div>
                <div class="finding-prompt">
                  <strong>Q:</strong> {{ r.prompt }}
                </div>
                <div v-if="r.mention_context" class="finding-context">
                  <strong>Match:</strong> "...{{ r.mention_context }}..."
                </div>
                <details v-if="r.response_text" class="finding-response">
                  <summary class="response-toggle">View full AI response ({{ r.response_text.length }} chars)</summary>
                  <pre class="response-pre">{{ r.response_text }}</pre>
                </details>
              </div>
            </div>
            <!-- Failed queries shown compactly -->
            <div v-else class="finding-card finding-failed">
              <div class="finding-number">#{{ i + 1 }}</div>
              <div class="finding-body">
                <div class="finding-header">
                  <span class="finding-provider">{{ providerLabel(r.provider) }}</span>
                  <span class="badge badge-danger">API Failed</span>
                </div>
                <div class="finding-error">{{ r.error_message }}</div>
              </div>
            </div>
          </template>
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

      <!-- How Scoring Works (when audit is completed, shown below) -->
      <div v-if="latestAudit && latestAudit.status === 'completed'" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showMethodology = !showMethodology">
          <h3 class="card-title">How This Score Was Calculated</h3>
          <span class="text-xs text-muted">{{ showMethodology ? 'Hide' : 'Show' }}</span>
        </div>
        <div v-if="showMethodology" class="methodology-content">
          <div class="method-steps">
            <div class="method-step">
              <div class="step-num">1</div>
              <div>
                <div class="step-title">Generate Prompts</div>
                <div class="step-desc">{{ auditDetail?.prompts?.length || latestAudit.prompts?.length || '?' }} natural-language questions were generated based on your business name, industry{{ latestAudit.location ? ', and location (' + latestAudit.location + ')' : '' }}.</div>
              </div>
            </div>
            <div class="method-step">
              <div class="step-num">2</div>
              <div>
                <div class="step-title">Query AI Providers</div>
                <div class="step-desc">Each prompt was sent to {{ (latestAudit.providers_queried || []).join(', ') || 'selected providers' }}. We ask the AI to list top options in your industry to simulate real user queries.</div>
              </div>
            </div>
            <div class="method-step">
              <div class="step-num">3</div>
              <div>
                <div class="step-title">Analyze Responses</div>
                <div class="step-desc">Each response is scanned for your business name. If found, we extract the rank position (e.g., listed 3rd out of 10) and the sentiment of the mention (positive, neutral, or negative).</div>
              </div>
            </div>
            <div class="method-step">
              <div class="step-num">4</div>
              <div>
                <div class="step-title">Compute Score</div>
                <div class="step-desc">
                  <strong>Mention Rate</strong> (40pts): % of queries where you appear.
                  <strong>Rank Position</strong> (35pts): Higher rank = more points (rank #1 → 35pts, #5 → 20pts).
                  <strong>Sentiment + Coverage</strong> (25pts): Positive mentions and multi-provider presence boost this.
                </div>
              </div>
            </div>
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
    <BaseModal v-model="showRunForm" title="Run LLM Ranking Audit">
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
      <template #footer>
        <button class="btn btn-secondary" @click="showRunForm = false">Cancel</button>
        <button class="btn btn-primary" @click="submitAudit" :disabled="running">
          {{ running ? 'Queuing...' : 'Start Audit' }}
        </button>
      </template>
    </BaseModal>

    <!-- Schedule Modal -->
    <BaseModal v-model="showScheduleModal" title="Schedule Periodic Audits">
      <p class="text-sm text-muted" style="margin-bottom:16px;line-height:1.5">
        Automatically run LLM ranking audits on a schedule so you can track visibility trends without manual effort.
      </p>
      <div class="form-group">
        <label class="form-label">Business Name</label>
        <input v-model="scheduleForm.business_name" class="form-input" placeholder="e.g. Acme Corp" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Industry</label>
        <input v-model="scheduleForm.industry" class="form-input" placeholder="e.g. SaaS, marketing" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Location (optional)</label>
        <input v-model="scheduleForm.location" class="form-input" placeholder="e.g. US, Europe" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Frequency</label>
        <select v-model="scheduleForm.frequency" class="form-input">
          <option value="weekly">Weekly</option>
          <option value="biweekly">Every 2 Weeks</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Providers</label>
        <div class="provider-checks">
          <label v-for="p in availableProviders" :key="p.value" class="check-label">
            <input type="checkbox" :value="p.value" v-model="scheduleForm.providers" />
            {{ p.label }}
          </label>
        </div>
      </div>
      <p v-if="scheduleError" class="form-error" style="margin-top:8px">{{ scheduleError }}</p>
      <template #footer>
        <button v-if="schedule" class="btn btn-danger" @click="deleteSchedule" style="margin-right:auto">Remove Schedule</button>
        <button class="btn btn-secondary" @click="showScheduleModal = false">Cancel</button>
        <button class="btn btn-primary" @click="saveSchedule" :disabled="savingSchedule">
          {{ savingSchedule ? 'Saving...' : 'Save Schedule' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import llmRankingApi from '@/api/llm_ranking'
import BaseModal from '@/components/ui/BaseModal.vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Filler, Tooltip, Legend,
)

ChartJS.defaults.color = '#8a8a9a'
ChartJS.defaults.font.family = "'Inter', 'SF Pro Display', system-ui, sans-serif"
ChartJS.defaults.font.size = 11

const route = useRoute()
const websiteId = route.params.websiteId
const toast = useToast()

const audits = ref([])
const history = ref([])
const loading = ref(true)
const running = ref(false)
const showRunForm = ref(false)
const auditError = ref('')
const selectedAuditId = ref(null)
const latestBreakdown = ref([])
const recommendations = ref([])
const auditDetail = ref(null)
const showFindings = ref(true)
const showMethodology = ref(false)
const showPrompts = ref(true)
const confirmDeleteId = ref(null)
const historyData = ref([])
let pollTimer = null

// Schedule state
const schedule = ref(null)
const showScheduleModal = ref(false)
const savingSchedule = ref(false)
const scheduleError = ref('')
const scheduleForm = ref({
  business_name: '',
  industry: '',
  location: '',
  frequency: 'weekly',
  providers: ['claude', 'gpt4', 'gemini', 'perplexity'],
})

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

const latestAudit = computed(() => {
  // Prefer the selected audit, fallback to first completed, then first overall
  if (selectedAuditId.value) {
    const selected = audits.value.find(a => a.id === selectedAuditId.value)
    if (selected) return selected
  }
  return audits.value.find(a => a.status === 'completed') || audits.value[0] || null
})

const isAuditComplete = computed(() => latestAudit.value?.status === 'completed')
const isAuditRunning = computed(() => {
  const s = latestAudit.value?.status
  return s === 'running' || s === 'pending'
})

// Live per-query results: sorted newest-first for the running ticker
const liveResults = computed(() => {
  const list = auditDetail.value?.results || []
  return [...list].reverse()
})

// ── Prompt Intelligence aggregation ─────────────────────────────────────────
const providerFilter = ref('')
const collapsedIntents = ref(new Set())

function toggleIntent(intent) {
  const s = new Set(collapsedIntents.value)
  if (s.has(intent)) s.delete(intent)
  else s.add(intent)
  collapsedIntents.value = s
}

const filteredResults = computed(() => {
  const results = auditDetail.value?.results || []
  if (!providerFilter.value) return results
  return results.filter(r => r.provider === providerFilter.value)
})

const availableProviderFilters = computed(() => {
  const set = new Set((auditDetail.value?.results || []).map(r => r.provider))
  return [...set]
})

const uniquePromptCount = computed(() => {
  return new Set((auditDetail.value?.results || []).map(r => r.prompt)).size
})

// Map prompt text -> intent, derived once from the audit's prompts list
const promptIntentByText = computed(() => {
  const map = {}
  const prompts = latestAudit.value?.prompts || []
  prompts.forEach((p, i) => { map[p] = promptIntents.value[i] || 'custom' })
  return map
})

// Build per-prompt aggregate rows from the filtered result set
const promptRows = computed(() => {
  const byPrompt = new Map()
  for (const r of filteredResults.value) {
    if (!byPrompt.has(r.prompt)) byPrompt.set(r.prompt, [])
    byPrompt.get(r.prompt).push(r)
  }

  const rows = []
  for (const [text, results] of byPrompt.entries()) {
    const succeeded = results.filter(r => r.query_succeeded)
    const mentioned = succeeded.filter(r => r.is_mentioned)
    const visibility = succeeded.length
      ? Math.round(mentioned.length / succeeded.length * 100)
      : 0
    const ranks = mentioned.map(r => r.mention_rank).filter(x => x != null)
    const avgRank = ranks.length
      ? (ranks.reduce((a, b) => a + b, 0) / ranks.length).toFixed(1).replace(/\.0$/, '')
      : null

    const providerDots = results.map(r => ({
      provider: r.provider,
      mentioned: r.is_mentioned,
      succeeded: r.query_succeeded,
      rank: r.mention_rank,
    }))

    // Aggregate competitors co-mentioned in this prompt's responses
    const compCounts = new Map()
    for (const r of results) {
      for (const c of (r.competitors_mentioned || [])) {
        if (!c?.name) continue
        compCounts.set(c.name, (compCounts.get(c.name) || 0) + 1)
      }
    }
    const topCompetitors = [...compCounts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)

    rows.push({
      text,
      intent: promptIntentByText.value[text] || 'custom',
      visibility,
      avgRank,
      providerDots,
      topCompetitors,
      responses: results.filter(r => r.query_succeeded && r.response_text),
    })
  }
  return rows
})

const intentGroups = computed(() => {
  const groups = {}
  for (const row of promptRows.value) {
    if (!groups[row.intent]) groups[row.intent] = []
    groups[row.intent].push(row)
  }
  return Object.entries(groups)
    .map(([intent, prompts]) => {
      const avgVisibility = prompts.length
        ? Math.round(prompts.reduce((a, p) => a + p.visibility, 0) / prompts.length)
        : 0
      return { intent, prompts, avgVisibility }
    })
    .sort((a, b) => b.avgVisibility - a.avgVisibility)
})

// Competitors leaderboard: aggregated across all prompts, not filtered
const competitorLeaderboard = computed(() => {
  const results = auditDetail.value?.results || []
  const stats = new Map()
  for (const r of results) {
    if (!r.query_succeeded) continue
    for (const c of (r.competitors_mentioned || [])) {
      if (!c?.name) continue
      if (!stats.has(c.name)) stats.set(c.name, { name: c.name, prompts: new Set(), ranks: [] })
      const s = stats.get(c.name)
      s.prompts.add(r.prompt)
      if (typeof c.position === 'number') s.ranks.push(c.position)
    }
  }
  return [...stats.values()]
    .map(s => ({
      name: s.name,
      promptCount: s.prompts.size,
      avgRank: s.ranks.length
        ? (s.ranks.reduce((a, b) => a + b, 0) / s.ranks.length).toFixed(1).replace(/\.0$/, '')
        : null,
    }))
    .sort((a, b) => b.promptCount - a.promptCount)
    .slice(0, 10)
})

function formatIntent(intent) {
  if (!intent) return 'Other'
  return intent.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function visibilityColor(pct) {
  if (pct >= 60) return 'var(--color-success, #10B981)'
  if (pct >= 30) return 'var(--color-warning, #F59E0B)'
  return 'var(--color-danger, #DC2626)'
}

function providerDotTitle(d) {
  if (!d.succeeded) return 'failed'
  if (d.mentioned) return `mentioned #${d.rank || '—'}`
  return 'not mentioned'
}

function sentimentBadge(s) {
  return s === 'positive' ? 'badge-success' : s === 'negative' ? 'badge-danger' : 'badge-neutral'
}

// Score factor breakdown (must sum to ~overall_score)
const mentionPts = computed(() => {
  const a = latestAudit.value
  if (!a) return 0
  return Math.round((a.mention_rate || 0) * 0.4)
})
const rankPts = computed(() => {
  const a = latestAudit.value
  if (!a || !a.avg_mention_rank || a.mention_rate === 0) return 0
  // rank #1 → 35pts, rank #10 → 0pts
  return Math.max(0, Math.round(35 * (1 - (a.avg_mention_rank - 1) / 9)))
})
const sentimentPts = computed(() => {
  const a = latestAudit.value
  if (!a) return 0
  return Math.max(0, (a.overall_score || 0) - mentionPts.value - rankPts.value)
})

// Findings stats
const successfulResults = computed(() => {
  if (!auditDetail.value?.results) return []
  return auditDetail.value.results.filter(r => r.query_succeeded)
})
const mentionedResults = computed(() => {
  return successfulResults.value.filter(r => r.is_mentioned)
})
const avgRankDisplay = computed(() => {
  const ranks = mentionedResults.value.map(r => r.mention_rank).filter(Boolean)
  if (!ranks.length) return 'N/A'
  return '#' + Math.round(ranks.reduce((a, b) => a + b, 0) / ranks.length)
})
const promptsUsed = computed(() => {
  if (!auditDetail.value?.results) return 0
  return new Set(auditDetail.value.results.filter(r => r.query_succeeded).map(r => r.prompt)).size
})

// ── Historic trend charts ──
const shortDate = (dt) => new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

const trendLabels = computed(() => history.value.map(h => shortDate(h.completed_at)))

const overallTrendData = computed(() => ({
  labels: trendLabels.value,
  datasets: [
    {
      label: 'Overall Score',
      data: history.value.map(h => h.overall_score ?? 0),
      borderColor: '#F5A623',
      backgroundColor: 'rgba(245, 166, 35, 0.12)',
      fill: true,
      tension: 0.35,
      borderWidth: 2.5,
      pointRadius: 3,
      pointHoverRadius: 5,
      yAxisID: 'y',
    },
    {
      label: 'Mention Rate (%)',
      data: history.value.map(h => Math.round(h.mention_rate || 0)),
      borderColor: '#5B8DEF',
      backgroundColor: 'rgba(91, 141, 239, 0.08)',
      fill: false,
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
      yAxisID: 'y',
    },
  ],
}))

const overallTrendOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: true, position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, boxWidth: 6 } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)', titleColor: '#fff', bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)', borderWidth: 1, padding: 12, cornerRadius: 8,
      displayColors: true, usePointStyle: true,
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 10, padding: 8 } },
    y: { grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false }, border: { display: false }, ticks: { padding: 10 }, beginAtZero: true, max: 100 },
  },
}

// Build per-provider datasets: one line per provider across all audits
const providerTrendDatasets = computed(() => {
  const providers = new Set()
  for (const h of history.value) {
    for (const p of (h.providers || [])) providers.add(p.provider)
  }
  return [...providers].map(key => {
    const meta = PROVIDER_META[key] || { label: key, color: '#6B7280' }
    return {
      label: meta.label,
      data: history.value.map(h => {
        const entry = (h.providers || []).find(x => x.provider === key)
        return entry ? entry.mention_rate : null
      }),
      borderColor: meta.color,
      backgroundColor: meta.color + '22',
      fill: false,
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
      spanGaps: true,
    }
  })
})

const providerTrendData = computed(() => ({
  labels: trendLabels.value,
  datasets: providerTrendDatasets.value,
}))

const providerTrendOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: true, position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, boxWidth: 6 } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)', titleColor: '#fff', bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)', borderWidth: 1, padding: 12, cornerRadius: 8,
      displayColors: true, usePointStyle: true,
      callbacks: {
        label: (ctx) => ctx.parsed.y == null ? `${ctx.dataset.label}: n/a` : `${ctx.dataset.label}: ${ctx.parsed.y}%`,
      },
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 10, padding: 8 } },
    y: {
      grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 10, callback: (v) => v + '%' },
      beginAtZero: true,
      max: 100,
      title: { display: true, text: 'Mention rate', color: '#8a8a9a', font: { size: 11 } },
    },
  },
}

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

// ── Chart Data ─────────────────────────────────────────────────────────────

const PROVIDER_COLORS = {
  claude: '#A78BFA',
  gpt4: '#34D399',
  gemini: '#5B8DEF',
  perplexity: '#F59E0B',
}

const providerChartData = computed(() => {
  const bd = latestBreakdown.value.filter(p => p.succeeded > 0)
  return {
    labels: bd.map(p => p.provider_display || providerLabel(p.provider)),
    datasets: [{
      label: 'Mention Rate (%)',
      data: bd.map(p => p.mention_rate),
      backgroundColor: bd.map(p => PROVIDER_COLORS[p.provider] || '#6B7280'),
      borderRadius: 6,
      barThickness: 36,
    }],
  }
})

const providerChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1e1e2e',
      padding: 10,
      cornerRadius: 8,
      callbacks: {
        label: (ctx) => `${ctx.parsed.y}% mention rate`,
      },
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      grid: { color: 'rgba(255,255,255,0.04)' },
      ticks: { callback: (v) => v + '%' },
    },
    x: {
      grid: { display: false },
    },
  },
}

const trendChartData = computed(() => {
  const history = historyData.value
  return {
    labels: history.map(h => {
      const d = new Date(h.completed_at)
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    }),
    datasets: [
      {
        label: 'Overall Score',
        data: history.map(h => h.overall_score),
        borderColor: '#A78BFA',
        backgroundColor: 'rgba(167,139,250,0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#A78BFA',
      },
      {
        label: 'Mention Rate (%)',
        data: history.map(h => h.mention_rate),
        borderColor: '#34D399',
        backgroundColor: 'rgba(52,211,153,0.06)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#34D399',
        borderDash: [4, 4],
      },
    ],
  }
})

const trendChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'bottom',
      labels: { usePointStyle: true, pointStyle: 'circle', padding: 16 },
    },
    tooltip: {
      backgroundColor: '#1e1e2e',
      padding: 10,
      cornerRadius: 8,
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      grid: { color: 'rgba(255,255,255,0.04)' },
      ticks: { callback: (v) => v },
    },
    x: {
      grid: { display: false },
    },
  },
}

// ── Helpers ─────────────────────────────────────────────────────────────────

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

function formatRelative(dt) {
  if (!dt) return '—'
  const d = new Date(dt)
  const now = new Date()
  const diffMs = d - now
  if (diffMs < 0) return 'any moment now'
  const diffDays = Math.ceil(diffMs / 86400000)
  if (diffDays <= 1) return 'tomorrow'
  if (diffDays <= 7) return `in ${diffDays} days`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
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
    // Show the prompts panel immediately so the user sees what's being asked
    auditDetail.value = audit
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

// ── Schedule Functions ─────────────────────────────────────────────────────

async function fetchSchedule() {
  try {
    const { data } = await llmRankingApi.getSchedule(websiteId)
    schedule.value = data?.data?.schedule || data?.schedule || null
    if (schedule.value) {
      scheduleForm.value = {
        business_name: schedule.value.business_name || '',
        industry: schedule.value.industry || '',
        location: schedule.value.location || '',
        frequency: schedule.value.frequency || 'weekly',
        providers: schedule.value.providers?.length ? schedule.value.providers : ['claude', 'gpt4', 'gemini', 'perplexity'],
      }
    }
  } catch (e) {
    console.error('Schedule fetch error', e)
  }
}

async function saveSchedule() {
  if (!scheduleForm.value.business_name) { scheduleError.value = 'Business name is required.'; return }
  if (!scheduleForm.value.industry) { scheduleError.value = 'Industry is required.'; return }
  savingSchedule.value = true
  scheduleError.value = ''
  try {
    const { data } = await llmRankingApi.saveSchedule(websiteId, {
      ...scheduleForm.value,
      is_enabled: true,
    })
    schedule.value = data?.data?.schedule || data?.schedule || null
    showScheduleModal.value = false
    toast.success('Schedule saved! Audits will run automatically.')
  } catch (err) {
    scheduleError.value = err.displayMessage || 'Failed to save schedule.'
  } finally {
    savingSchedule.value = false
  }
}

async function disableSchedule() {
  try {
    await llmRankingApi.deleteSchedule(websiteId)
    schedule.value = null
    toast.success('Schedule disabled.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to disable schedule.')
  }
}

async function deleteSchedule() {
  try {
    await llmRankingApi.deleteSchedule(websiteId)
    schedule.value = null
    showScheduleModal.value = false
    toast.success('Schedule removed.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to remove schedule.')
  }
}

// ── History ────────────────────────────────────────────────────────────────

async function fetchHistory() {
  try {
    const { data } = await llmRankingApi.history(websiteId)
    historyData.value = data?.data || data || []
  } catch (e) {
    console.error('History fetch error', e)
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
      let anyCompleted = false
      for (const newA of newAudits) {
        const oldA = audits.value.find(a => a.id === newA.id)
        if (oldA && (oldA.status === 'pending' || oldA.status === 'running') && newA.status === 'completed') {
          toast.success(`Audit for "${newA.business_name}" completed! Score: ${newA.overall_score}/100`)
          anyCompleted = true
        }
      }
      audits.value = newAudits
      if (audits.value.length && audits.value[0].status === 'completed' && !latestBreakdown.value.length) {
        await selectAudit(audits.value[0])
        await fetchHistory()
      }
      // During a running audit, fetch partial results so the live ticker
      // updates as each LLM finishes — without blocking on /breakdown/ or
      // /recommendations/ which require a completed audit.
      const selected = audits.value.find(a => a.id === selectedAuditId.value)
      if (selected && (selected.status === 'running' || selected.status === 'pending')) {
        try {
          const dRes = await llmRankingApi.getAudit(websiteId, selected.id)
          auditDetail.value = dRes.data?.data || dRes.data || null
        } catch (_) { /* ignore partial fetch errors */ }
      }
      if (anyCompleted) {
        await fetchHistory()
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

async function fetchHistory() {
  try {
    const { data } = await llmRankingApi.history(websiteId)
    history.value = data?.data || data || []
  } catch (e) {
    console.error('LLM ranking history fetch error', e)
    history.value = []
  }
}

async function fetchData() {
  loading.value = true
  try {
    const [listRes] = await Promise.all([
      llmRankingApi.listAudits(websiteId),
      fetchHistory(),
    ])
    const { data } = listRes
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

onMounted(async () => {
  await Promise.all([fetchData(), fetchHistory(), fetchSchedule()])
})
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* Header actions */
.header-actions { display: flex; gap: 8px; align-items: center; }

/* Schedule banner */
.schedule-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  background: rgba(167, 139, 250, 0.08);
  border: 1px solid rgba(167, 139, 250, 0.2);
  margin-bottom: 20px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
}
.schedule-banner strong { color: var(--text-primary); }
.btn-xs { font-size: var(--font-xs); padding: 2px 8px; }

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
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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
  border: none;
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  transition: border-color var(--transition-fast);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
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

/* Charts row */
.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}
.chart-card { overflow: hidden; }
.chart-wrap {
  padding: 16px;
  height: 260px;
}

/* Methodology */
.methodology-content { padding: 16px; }
.method-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.method-item {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  text-align: center;
}
.method-weight {
  font-size: var(--font-lg);
  font-weight: 800;
  color: var(--color-primary);
  margin-bottom: 4px;
}
.method-title {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.method-desc {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.5;
}
.method-steps { display: flex; flex-direction: column; gap: 16px; padding: 16px; }
.method-step { display: flex; gap: 12px; align-items: flex-start; }
.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
  font-size: var(--font-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-title { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); margin-bottom: 2px; }
.step-desc { font-size: var(--font-xs); color: var(--text-muted); line-height: 1.6; }

/* Score factor bars */
.score-factors {
  padding: 16px;
  border-top: 1px solid var(--border-color);
}
.factor-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.factor-label {
  width: 180px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}
.factor-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}
.factor-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
  min-width: 2px;
}
.factor-value {
  width: 50px;
  text-align: right;
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-primary);
}
.factor-total {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  font-size: var(--font-sm);
  color: var(--text-primary);
}

/* Visibility trend charts */
.trends-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px;
}
@media (max-width: 900px) {
  .trends-grid { grid-template-columns: 1fr; }
}
.trend-block {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.trend-label {
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}
.trend-chart-wrap {
  position: relative;
  height: 240px;
}

/* Findings summary */
.findings-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.summary-stat {
  text-align: center;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.summary-num {
  display: block;
  font-size: var(--font-lg);
  font-weight: 800;
  color: var(--text-primary);
}
.summary-label {
  font-size: var(--font-xs);
  color: var(--text-muted);
}

/* Detailed Findings */
.findings-list { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.finding-card {
  display: flex;
  gap: 12px;
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--text-muted);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  background: var(--bg-base);
}
.finding-card.finding-mentioned { border-left-color: var(--color-success); }
.finding-card.finding-failed { border-left-color: var(--color-danger); opacity: 0.5; }
.finding-number {
  font-size: var(--font-xs);
  font-weight: 800;
  color: var(--text-muted);
  padding-top: 2px;
  flex-shrink: 0;
  width: 24px;
}
.finding-body { flex: 1; min-width: 0; }
.finding-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.finding-provider { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); }
.finding-confidence { font-size: var(--font-xs); color: var(--text-muted); margin-left: auto; }
.finding-label { font-weight: 600; color: var(--text-muted); font-size: var(--font-xs); text-transform: uppercase; letter-spacing: 0.5px; }
.finding-prompt { font-size: var(--font-sm); color: var(--text-secondary); margin-bottom: 6px; line-height: 1.5; }
.finding-context { font-size: var(--font-sm); color: var(--color-success); font-style: italic; margin-bottom: 6px; }
.finding-error { font-size: var(--font-xs); color: var(--color-danger); margin-bottom: 6px; }
.finding-response { margin-top: 8px; }
.response-toggle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
}
.response-toggle:hover { color: var(--text-primary); }
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

/* Prompt list (shown before / during an audit) */
.prompt-list { display: flex; flex-direction: column; gap: 6px; padding: 16px; }
.prompt-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  font-size: var(--font-sm);
}
.prompt-num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--bg-surface);
  color: var(--text-muted);
  font-weight: 700;
  font-size: var(--font-xs);
  display: flex;
  align-items: center;
  justify-content: center;
}
.prompt-text {
  flex: 1;
  color: var(--text-primary);
  line-height: 1.45;
}
.prompt-intent {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(91, 141, 239, 0.12);
  color: #3B5EAF;
}

/* Prompt Intelligence (post-audit rich view) */
.pi-filter { display: flex; align-items: center; }
.pi-select {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: var(--font-xs);
  font-weight: 600;
}
.pi-groups { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.pi-group {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-base);
  overflow: hidden;
}
.pi-group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  background: var(--bg-surface);
  user-select: none;
}
.pi-group-header:hover { background: rgba(0,0,0,0.02); }
.pi-chevron { color: var(--text-muted); transition: transform 0.2s; flex-shrink: 0; }
.pi-chevron.open { transform: rotate(90deg); }
.pi-intent-name {
  font-size: var(--font-xs);
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-primary);
}
.pi-group-stats {
  font-size: var(--font-xs);
  color: var(--text-muted);
  flex: 0 0 auto;
  margin-left: auto;
}
.pi-vis-bar-wrap {
  flex: 0 0 80px;
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
  margin-left: 8px;
}
.pi-vis-bar {
  display: block;
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.pi-group-body { display: flex; flex-direction: column; padding: 4px 0; }
.pi-prompt {
  padding: 12px 14px;
  border-top: 1px solid var(--border-color);
}
.pi-prompt:first-child { border-top: none; }
.pi-prompt-text {
  font-size: var(--font-sm);
  color: var(--text-primary);
  font-weight: 500;
  line-height: 1.45;
  margin-bottom: 8px;
}
.pi-prompt-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.pi-stat { display: inline-flex; align-items: center; gap: 4px; }
.pi-stat strong { font-weight: 700; color: var(--text-primary); }
.pi-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--border-color);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 800;
  margin-left: 2px;
  cursor: help;
}
.pi-dot.hit  { background: var(--color-success, #10B981); color: #fff; }
.pi-dot.fail { background: var(--color-danger, #DC2626); color: #fff; opacity: 0.7; }

.pi-competitors {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: var(--font-xs);
}
.pi-comp-label { color: var(--text-muted); font-weight: 600; margin-right: 2px; }
.pi-comp-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-weight: 500;
}
.pi-comp-count {
  color: var(--text-muted);
  margin-left: 4px;
  font-weight: 600;
}

.pi-responses { margin-top: 10px; }
.pi-responses-toggle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
}
.pi-responses-toggle:hover { color: var(--text-primary); }
.pi-response {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
}
.pi-response-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.pi-response-provider { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); }
.pi-response-text {
  margin: 0;
  font-size: var(--font-xs);
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow-y: auto;
  color: var(--text-secondary);
  font-family: inherit;
}

/* Competitors leaderboard */
.comp-leaderboard { display: flex; flex-direction: column; padding: 16px 16px 0; gap: 6px; }
.comp-row {
  display: grid;
  grid-template-columns: 24px 1fr 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  font-size: var(--font-sm);
}
.comp-rank {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: var(--font-md);
  color: var(--text-muted);
  text-align: center;
}
.comp-name { font-weight: 700; color: var(--text-primary); }
.comp-bar-wrap {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}
.comp-bar {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #5B8DEF, #A78BFA);
  border-radius: 3px;
  transition: width 0.5s ease;
}
.comp-coverage { font-size: var(--font-xs); color: var(--text-muted); white-space: nowrap; }
.comp-avg-rank {
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-primary);
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-surface);
}

/* Live ticker (during a running audit) */
.live-pulse {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success, #34D399);
  margin-left: 8px;
  animation: live-pulse-kf 1.3s ease-in-out infinite;
  vertical-align: middle;
}
@keyframes live-pulse-kf {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52,211,153,0.6); }
  50%      { opacity: 0.6; box-shadow: 0 0 0 6px rgba(52,211,153,0); }
}
.live-list { display: flex; flex-direction: column; gap: 6px; padding: 16px; }
.live-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--text-muted);
  font-size: var(--font-sm);
  animation: live-row-in 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.live-row.live-hit  { border-left-color: var(--color-success, #34D399); }
.live-row.live-fail { border-left-color: var(--color-danger, #DC2626); opacity: 0.7; }
.live-provider {
  flex-shrink: 0;
  font-weight: 700;
  color: var(--text-primary);
  width: 76px;
}
.live-prompt {
  flex: 1;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
@keyframes live-row-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
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
