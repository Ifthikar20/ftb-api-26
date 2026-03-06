<template>
  <div class="audits-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Audits</h1>
        <p class="page-subtitle">Automated SEO, performance, and security checks.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="runAudit" :disabled="running">{{ running ? 'Running...' : 'Run Audit' }}</button>
    </div>

    <div v-if="loading" class="loading-state">Loading audits...</div>
    <template v-else>
      <!-- Latest Audit Scores -->
      <div v-if="latest" class="stats-grid" style="margin-bottom:24px">
        <div class="stat-card" v-for="s in scoreCards" :key="s.label">
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-value" :class="scoreColor(s.value)">{{ s.value || '--' }}</div>
        </div>
      </div>

      <!-- Issues -->
      <div class="card" style="margin-bottom:20px" v-if="issues.length">
        <div class="card-header">
          <h3 class="card-title">Issues Found</h3>
          <span class="text-sm text-muted">{{ issues.length }} total</span>
        </div>
        <div class="issues-list">
          <div v-for="issue in issues" :key="issue.id || issue.title" class="issue-item">
            <span class="badge" :class="severityClass(issue.severity)">{{ issue.severity }}</span>
            <div class="issue-content">
              <div class="font-semibold text-sm">{{ issue.title }}</div>
              <div class="text-xs text-muted">{{ issue.recommendation }}</div>
            </div>
            <span class="text-xs text-muted">{{ issue.category }}</span>
          </div>
        </div>
      </div>

      <!-- Audit History -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">Audit History</h3></div>
        <table class="data-table" v-if="history.length">
          <thead><tr><th>Date</th><th>Score</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="a in history" :key="a.id">
              <td>{{ formatDate(a.triggered_at) }}</td>
              <td class="font-semibold">{{ a.overall_score || '--' }}</td>
              <td><span class="badge" :class="a.status === 'completed' ? 'badge-success' : 'badge-neutral'">{{ a.status }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">No audit history. Run your first audit.</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import auditsApi from '@/api/audits'

const route = useRoute()
const websiteId = route.params.websiteId

const loading = ref(true)
const running = ref(false)
const latest = ref(null)
const issues = ref([])
const history = ref([])

const scoreCards = computed(() => {
  if (!latest.value) return []
  return [
    { label: 'Overall', value: latest.value.overall_score },
    { label: 'SEO', value: latest.value.seo_score },
    { label: 'Performance', value: latest.value.performance_score },
    { label: 'Mobile', value: latest.value.mobile_score },
    { label: 'Security', value: latest.value.security_score },
    { label: 'Content', value: latest.value.content_score },
  ]
})

function scoreColor(v) {
  if (v >= 80) return 'text-success'
  if (v >= 60) return 'text-warning'
  return 'text-danger'
}

function severityClass(s) {
  const map = { critical: 'badge-danger', warning: 'badge-warning', info: 'badge-info' }
  return map[s] || 'badge-neutral'
}

function formatDate(d) {
  if (!d) return '--'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

async function fetchData() {
  loading.value = true
  try {
    const [latestRes, historyRes] = await Promise.all([
      auditsApi.latest(websiteId).catch(() => ({ data: null })),
      auditsApi.history(websiteId).catch(() => ({ data: [] })),
    ])
    const l = latestRes.data?.data || latestRes.data
    latest.value = l || null
    issues.value = l?.issues || []
    history.value = historyRes.data?.data || historyRes.data || []
  } catch (e) {
    console.error('Audits fetch error', e)
  } finally {
    loading.value = false
  }
}

async function runAudit() {
  running.value = true
  try {
    await auditsApi.run(websiteId)
    setTimeout(() => { fetchData(); running.value = false }, 3000)
  } catch {
    running.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }
.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-danger { color: var(--color-danger); }

.issues-list { display: flex; flex-direction: column; }
.issue-item { display: flex; align-items: flex-start; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border-color); }
.issue-item:last-child { border-bottom: none; }
.issue-content { flex: 1; }
</style>
