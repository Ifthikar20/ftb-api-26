<template>
  <div class="agents-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">AI Agents</h1>
        <p class="page-subtitle">Autonomous workflows that find opportunities and run campaigns for you.</p>
      </div>
      <div class="header-actions">
        <div class="trigger-dropdown" v-if="showDropdown" @click.stop>
          <div v-for="at in agentTypes" :key="at.id" class="dropdown-item" @click="triggerAgent(at.id)">
            <span class="dropdown-icon">{{ at.icon }}</span>
            <div>
              <div class="dropdown-name">{{ at.name }}</div>
              <div class="dropdown-desc">{{ at.description }}</div>
            </div>
          </div>
        </div>
        <button class="btn btn-primary btn-sm" @click.stop="showDropdown = !showDropdown" :disabled="triggering">
          {{ triggering ? 'Starting...' : '+ Run Agent' }}
        </button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-grid" style="margin-bottom: 24px">
      <div class="stat-card">
        <div class="stat-label">Runs Today</div>
        <div class="stat-value">{{ runsToday }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Completed</div>
        <div class="stat-value text-success">{{ completedCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Awaiting Approval</div>
        <div class="stat-value" :class="pausedCount > 0 ? 'text-warning' : ''">{{ pausedCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Actions Taken</div>
        <div class="stat-value">{{ totalSteps }}</div>
      </div>
    </div>

    <!-- Approval Cards -->
    <div v-if="pausedRuns.length" class="approval-section">
      <h3 class="section-title">⏸ Awaiting Your Approval</h3>
      <div class="approval-cards">
        <div v-for="run in pausedRuns" :key="run.id" class="approval-card">
          <div class="approval-header">
            <span class="agent-icon">{{ getIcon(run.agent_type) }}</span>
            <div>
              <div class="font-semibold">{{ run.agent_type_display }}</div>
              <div class="text-xs text-muted">{{ run.website_name }} · {{ timeAgo(run.created_at) }}</div>
            </div>
          </div>
          <p class="approval-text">{{ run.summary || 'The agent has completed its analysis and needs your approval to proceed.' }}</p>
          <div class="approval-actions">
            <button class="btn btn-primary btn-sm" @click="approveRun(run)" :disabled="run._approving">
              {{ run._approving ? 'Approving...' : '✓ Approve' }}
            </button>
            <button class="btn btn-secondary btn-sm" @click="cancelRun(run)">✗ Reject</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Activity Feed -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Agent Activity</h3>
        <div class="filter-pills">
          <button v-for="f in filters" :key="f.value" class="filter-pill" :class="{ active: activeFilter === f.value }" @click="activeFilter = f.value">
            {{ f.label }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">Loading agent activity...</div>
      <div v-else-if="!filteredRuns.length" class="empty-state">
        <div class="empty-icon">🤖</div>
        <div>No agent runs yet. Click <strong>+ Run Agent</strong> to start your first one.</div>
      </div>
      <div v-else class="activity-feed">
        <div v-for="run in filteredRuns" :key="run.id" class="activity-item" :class="{ expanded: expandedRun === run.id }" @click="toggleExpand(run)">
          <div class="activity-row">
            <span class="agent-icon">{{ getIcon(run.agent_type) }}</span>
            <div class="activity-info">
              <div class="activity-title">
                {{ run.agent_type_display }}
                <span class="badge" :class="statusClass(run.status)">{{ run.status_display || run.status }}</span>
              </div>
              <div class="text-xs text-muted">{{ run.website_name }} · {{ timeAgo(run.created_at) }}</div>
            </div>
            <div class="activity-meta">
              <span class="text-xs text-muted" v-if="run.steps_count">{{ run.steps_count }} steps</span>
              <span class="text-xs text-muted" v-if="run.duration_ms">· {{ (run.duration_ms / 1000).toFixed(1) }}s</span>
              <svg class="expand-arrow" :class="{ rotated: expandedRun === run.id }" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4,6 8,10 12,6"/></svg>
            </div>
          </div>

          <!-- Expanded Detail -->
          <div v-if="expandedRun === run.id" class="activity-detail" @click.stop>
            <div v-if="run.summary" class="detail-summary">
              <strong>Summary:</strong> {{ run.summary }}
            </div>

            <!-- Findings -->
            <div v-if="run.findings && run.findings.length" class="findings-list">
              <div v-for="(f, i) in run.findings" :key="i" class="finding-item">
                <span class="finding-impact" :class="'impact-' + (f.impact || 'medium')">{{ f.impact || 'medium' }}</span>
                <div>
                  <div class="font-semibold text-sm">{{ f.title }}</div>
                  <div class="text-xs text-muted">{{ f.description }}</div>
                  <div v-if="f.action" class="text-xs" style="color: var(--brand-accent); margin-top:4px">→ {{ f.action }}</div>
                </div>
              </div>
            </div>

            <!-- Step Timeline -->
            <div v-if="detailSteps.length" class="steps-timeline">
              <h4 class="detail-section-title">Execution Steps</h4>
              <div v-for="step in detailSteps" :key="step.id" class="step-item">
                <div class="step-marker" :class="'step-' + step.status">
                  <span v-if="step.status === 'completed'">✓</span>
                  <span v-else-if="step.status === 'failed'">✗</span>
                  <span v-else-if="step.status === 'running'">⟳</span>
                  <span v-else>–</span>
                </div>
                <div class="step-content">
                  <div class="step-header">
                    <span class="step-tool">{{ formatToolName(step.tool_name) }}</span>
                    <span class="text-xs text-muted" v-if="step.duration_ms">{{ step.duration_ms }}ms</span>
                  </div>
                  <div class="step-reasoning text-xs text-muted">{{ step.reasoning }}</div>
                </div>
              </div>
            </div>

            <div v-if="run.error_message" class="detail-error">
              <strong>Error:</strong> {{ run.error_message }}
            </div>

            <div class="detail-footer">
              <button v-if="run.status === 'running' || run.status === 'paused'" class="btn btn-secondary btn-sm" @click.stop="cancelRun(run)">Cancel</button>
              <button v-if="run.status === 'paused'" class="btn btn-primary btn-sm" @click.stop="approveRun(run)">Approve</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import agentsApi from '@/api/agents'

const route = useRoute()
const websiteId = route.params.websiteId

const loading = ref(true)
const runs = ref([])
const agentTypes = ref([])
const showDropdown = ref(false)
const triggering = ref(false)
const expandedRun = ref(null)
const detailSteps = ref([])
const activeFilter = ref('all')
let pollInterval = null

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Running', value: 'running' },
  { label: 'Completed', value: 'completed' },
  { label: 'Paused', value: 'paused' },
  { label: 'Failed', value: 'failed' },
]

const filteredRuns = computed(() => {
  if (activeFilter.value === 'all') return runs.value
  return runs.value.filter(r => r.status === activeFilter.value)
})

const pausedRuns = computed(() => runs.value.filter(r => r.status === 'paused'))
const runsToday = computed(() => {
  const today = new Date().toISOString().split('T')[0]
  return runs.value.filter(r => r.created_at?.startsWith(today)).length
})
const completedCount = computed(() => runs.value.filter(r => r.status === 'completed').length)
const pausedCount = computed(() => pausedRuns.value.length)
const totalSteps = computed(() => runs.value.reduce((s, r) => s + (r.steps_count || 0), 0))

const iconMap = {
  opportunity_finder: '🎯',
  campaign_runner: '📝',
  competitor_watcher: '🕵️',
  anomaly_responder: '🔥',
}

function getIcon(type) { return iconMap[type] || '🤖' }

function statusClass(s) {
  const map = {
    completed: 'badge-success',
    running: 'badge-running',
    paused: 'badge-warning',
    failed: 'badge-danger',
    pending: 'badge-neutral',
    cancelled: 'badge-neutral',
  }
  return map[s] || 'badge-neutral'
}

function formatToolName(name) {
  return (name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

async function fetchRuns() {
  try {
    const res = await agentsApi.runs(websiteId)
    runs.value = (res.data || res || []).map(r => ({ ...r, _approving: false }))
  } catch (e) {
    console.error('Agent runs fetch error', e)
  }
}

async function fetchTypes() {
  try {
    const res = await agentsApi.types()
    agentTypes.value = res.data || res || []
  } catch (e) {
    console.error('Agent types fetch error', e)
  }
}

async function triggerAgent(agentType) {
  triggering.value = true
  showDropdown.value = false
  try {
    await agentsApi.trigger(websiteId, agentType)
    await fetchRuns()
  } catch (e) {
    console.error('Trigger failed', e)
  } finally {
    triggering.value = false
  }
}

async function approveRun(run) {
  run._approving = true
  try {
    await agentsApi.approve(websiteId, run.id)
    await fetchRuns()
  } catch (e) {
    console.error('Approve failed', e)
  } finally {
    run._approving = false
  }
}

async function cancelRun(run) {
  try {
    await agentsApi.cancel(websiteId, run.id)
    await fetchRuns()
  } catch (e) {
    console.error('Cancel failed', e)
  }
}

async function toggleExpand(run) {
  if (expandedRun.value === run.id) {
    expandedRun.value = null
    detailSteps.value = []
    return
  }
  expandedRun.value = run.id
  try {
    const res = await agentsApi.runDetail(websiteId, run.id)
    const detail = res.data || res
    detailSteps.value = detail.steps || []
    // Update local run with full data
    const idx = runs.value.findIndex(r => r.id === run.id)
    if (idx !== -1) {
      runs.value[idx] = { ...runs.value[idx], ...detail, _approving: false }
    }
  } catch (e) {
    detailSteps.value = []
  }
}

// Close dropdown on outside click
function closeDropdown() { showDropdown.value = false }

onMounted(async () => {
  document.addEventListener('click', closeDropdown)
  await Promise.all([fetchRuns(), fetchTypes()])
  loading.value = false
  // Poll for updates every 10s
  pollInterval = setInterval(fetchRuns, 10000)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeDropdown)
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }

/* Header */
.header-actions { position: relative; }

.trigger-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 320px;
  z-index: 100;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.dropdown-item:hover { background: var(--bg-surface); }
.dropdown-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
.dropdown-name { font-weight: 600; font-size: var(--font-sm); color: var(--text-primary); }
.dropdown-desc { font-size: var(--font-xs); color: var(--text-muted); margin-top: 2px; }

/* Section title */
.section-title { font-size: var(--font-md); font-weight: 700; color: var(--text-primary); margin-bottom: 12px; }

/* Approval Cards */
.approval-section { margin-bottom: 24px; }
.approval-cards { display: grid; gap: 16px; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }

.approval-card {
  background: var(--bg-card);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: 0 0 0 1px rgba(255, 180, 60, 0.15);
}

.approval-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.approval-text { font-size: var(--font-sm); color: var(--text-secondary); margin-bottom: 16px; line-height: 1.5; }
.approval-actions { display: flex; gap: 8px; }

/* Filter Pills */
.filter-pills { display: flex; gap: 6px; }
.filter-pill {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: var(--font-xs);
  font-weight: 600;
  background: var(--bg-surface);
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.filter-pill:hover { color: var(--text-primary); }
.filter-pill.active { background: var(--text-primary); color: var(--text-inverse); }

/* Activity Feed */
.activity-feed { display: flex; flex-direction: column; }

.activity-item {
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.activity-item:last-child { border-bottom: none; }
.activity-item:hover { background: var(--bg-surface); }

.activity-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
}

.agent-icon { font-size: 22px; flex-shrink: 0; }
.activity-info { flex: 1; min-width: 0; }
.activity-title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: var(--font-sm); }
.activity-meta { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.expand-arrow {
  color: var(--text-muted);
  transition: transform var(--transition-fast);
  margin-left: 8px;
}
.expand-arrow.rotated { transform: rotate(180deg); }

/* Badges */
.badge-running { background: rgba(59, 130, 246, 0.15); color: #3b82f6; animation: pulse-badge 2s infinite; }
@keyframes pulse-badge { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

/* Expanded Detail */
.activity-detail {
  padding: 0 16px 16px 52px;
  cursor: default;
}

.detail-summary {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-md);
}

.detail-section-title {
  font-size: var(--font-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 10px;
}

/* Findings */
.findings-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.finding-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-md);
}

.finding-impact {
  font-size: var(--font-xs);
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  height: fit-content;
  margin-top: 2px;
}
.impact-high { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.impact-medium { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.impact-low { background: rgba(34, 197, 94, 0.15); color: #22c55e; }

/* Step Timeline */
.steps-timeline { margin-bottom: 16px; }

.step-item {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  position: relative;
}

.step-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 30px;
  bottom: -8px;
  width: 2px;
  background: var(--border-color);
}

.step-marker {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex-shrink: 0;
  font-weight: 700;
}
.step-completed { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.step-failed { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.step-running { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.step-skipped { background: var(--bg-surface); color: var(--text-muted); }

.step-content { flex: 1; min-width: 0; }
.step-header { display: flex; justify-content: space-between; align-items: center; }
.step-tool { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.step-reasoning { margin-top: 2px; line-height: 1.4; }

.detail-error {
  font-size: var(--font-sm);
  color: var(--color-danger);
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
}

.detail-footer { display: flex; gap: 8px; justify-content: flex-end; }

@media (max-width: 768px) {
  .approval-cards { grid-template-columns: 1fr; }
  .activity-detail { padding-left: 16px; }
}
</style>
