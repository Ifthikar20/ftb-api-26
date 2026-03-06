<template>
  <div class="leads-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Leads</h1>
        <p class="page-subtitle">Track, score, and manage your website leads.</p>
      </div>
      <div class="flex gap-8">
        <select class="form-input" v-model="statusFilter" @change="fetchData" style="width:auto">
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="qualified">Qualified</option>
          <option value="customer">Customer</option>
          <option value="lost">Lost</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="handleExport">Export CSV</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading leads...</div>
    <template v-else>
      <div class="stats-grid" style="margin-bottom: 24px">
        <div class="stat-card">
          <div class="stat-label">Total Leads</div>
          <div class="stat-value">{{ leads.length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Hot Leads</div>
          <div class="stat-value">{{ hotCount }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Score</div>
          <div class="stat-value">{{ avgScore }}</div>
        </div>
      </div>

      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Company</th>
              <th>Score</th>
              <th>Status</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="lead in leads" :key="lead.id">
              <td>
                <div class="lead-name">{{ lead.name || 'Anonymous' }}</div>
                <div class="text-xs text-muted">{{ lead.email }}</div>
              </td>
              <td>{{ lead.company || '--' }}</td>
              <td>
                <span class="score-badge" :class="scoreTier(lead.score)">{{ lead.score }}</span>
              </td>
              <td>
                <span class="badge" :class="statusClass(lead.status)">{{ lead.status }}</span>
              </td>
              <td class="text-muted text-sm">{{ lead.source }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="leads.length === 0" class="empty-state">No leads found.</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import leadsApi from '@/api/leads'

const route = useRoute()
const websiteId = route.params.websiteId

const loading = ref(true)
const leads = ref([])
const statusFilter = ref('')

const hotCount = computed(() => leads.value.filter(l => l.score >= 70).length)
const avgScore = computed(() => {
  if (leads.value.length === 0) return 0
  return Math.round(leads.value.reduce((sum, l) => sum + (l.score || 0), 0) / leads.value.length)
})

function scoreTier(score) {
  if (score >= 80) return 'score-hot'
  if (score >= 50) return 'score-warm'
  return 'score-cold'
}

function statusClass(s) {
  const map = { new: 'badge-neutral', contacted: 'badge-info', qualified: 'badge-warning', customer: 'badge-success', lost: 'badge-danger' }
  return map[s] || 'badge-neutral'
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await leadsApi.list(websiteId, params)
    leads.value = data?.results || data?.data?.results || data?.data || data || []
  } catch (e) {
    console.error('Leads fetch error', e)
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  try {
    await leadsApi.export(websiteId)
  } catch {}
}

onMounted(fetchData)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }

.lead-name { font-weight: 600; color: var(--text-primary); }

.score-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--font-xs);
  font-weight: 700;
}

.score-hot { background: rgba(231, 76, 60, 0.12); color: var(--color-danger); }
.score-warm { background: rgba(243, 156, 18, 0.12); color: var(--color-warning); }
.score-cold { background: var(--bg-surface); color: var(--text-muted); }
</style>
