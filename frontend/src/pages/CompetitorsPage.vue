<template>
  <div class="competitors-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Competitors</h1>
        <p class="page-subtitle">Monitor your competition and find growth opportunities.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="showAdd = true">+ Add Competitor</button>
    </div>

    <div v-if="loading" class="loading-state">Loading competitors...</div>
    <template v-else>
      <!-- Competitors Table -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header"><h3 class="card-title">Tracked Competitors</h3></div>
        <table class="data-table">
          <thead>
            <tr><th>Name</th><th>Domain</th><th>Traffic</th><th>DA</th><th>Threat</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in competitors" :key="c.id">
              <td class="font-semibold">{{ c.name }}</td>
              <td class="text-muted text-sm">{{ c.competitor_url }}</td>
              <td>{{ c.estimated_traffic ? c.estimated_traffic.toLocaleString() : '--' }}</td>
              <td>{{ c.domain_authority || '--' }}</td>
              <td><span class="badge" :class="threatClass(c.threat_level)">{{ c.threat_level }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-if="competitors.length === 0" class="empty-state">No competitors tracked yet.</div>
      </div>

      <!-- Recent Changes -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header"><h3 class="card-title">Recent Changes</h3></div>
        <div class="changes-list" v-if="changes.length">
          <div v-for="ch in changes" :key="ch.id" class="change-item">
            <span class="badge" :class="changeClass(ch.change_type)">{{ formatChangeType(ch.change_type) }}</span>
            <div class="change-detail">
              <span class="text-sm font-semibold">{{ ch.competitor?.name || 'Competitor' }}</span>
              <span class="text-sm text-muted"> &mdash; {{ ch.detail?.title || ch.detail?.keyword || ch.detail?.url || JSON.stringify(ch.detail) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">No changes detected yet.</div>
      </div>

      <!-- Keyword Gaps -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">Keyword Gaps</h3></div>
        <table class="data-table" v-if="keywords.length">
          <thead><tr><th>Keyword</th><th>Your Rank</th><th>Volume</th><th>Difficulty</th><th>Opportunity</th></tr></thead>
          <tbody>
            <tr v-for="kw in keywords" :key="kw.keyword">
              <td class="font-semibold">{{ kw.keyword }}</td>
              <td>{{ kw.your_rank || 'Not ranking' }}</td>
              <td>{{ kw.search_volume?.toLocaleString() || '--' }}</td>
              <td>{{ kw.difficulty || '--' }}</td>
              <td>
                <div class="opp-bar">
                  <div class="opp-fill" :style="{ width: (kw.opportunity_score * 100) + '%' }"></div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">No keyword gap data available.</div>
      </div>
    </template>

    <!-- Add Modal -->
    <div v-if="showAdd" class="modal-overlay" @click.self="showAdd = false">
      <div class="modal-card">
        <h3 class="card-title" style="margin-bottom:16px">Add Competitor</h3>
        <div class="form-group">
          <label class="form-label">Name</label>
          <input v-model="newName" class="form-input" placeholder="e.g. RivalCo" />
        </div>
        <div class="form-group">
          <label class="form-label">URL</label>
          <input v-model="newUrl" class="form-input" placeholder="https://rivalco.io" />
        </div>
        <div class="flex gap-8" style="margin-top:16px">
          <button class="btn btn-primary" @click="addCompetitor">Add</button>
          <button class="btn btn-secondary" @click="showAdd = false">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import competitorsApi from '@/api/competitors'

const route = useRoute()
const websiteId = route.params.websiteId

const loading = ref(true)
const competitors = ref([])
const changes = ref([])
const keywords = ref([])
const showAdd = ref(false)
const newName = ref('')
const newUrl = ref('')

function threatClass(t) {
  const map = { critical: 'badge-danger', high: 'badge-warning', medium: 'badge-info', low: 'badge-neutral' }
  return map[t] || 'badge-neutral'
}

function changeClass(t) {
  const map = { new_page: 'badge-info', ranking_change: 'badge-warning', content_update: 'badge-neutral', pricing_change: 'badge-danger', removed_page: 'badge-danger' }
  return map[t] || 'badge-neutral'
}

function formatChangeType(t) { return (t || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }

async function fetchData() {
  loading.value = true
  try {
    const [compRes, changesRes] = await Promise.all([
      competitorsApi.list(websiteId),
      competitorsApi.changes(websiteId).catch(() => ({ data: [] })),
    ])
    competitors.value = compRes.data?.data || compRes.data || []
    changes.value = changesRes.data?.data || changesRes.data || []
  } catch (e) {
    console.error('Competitors fetch error', e)
  } finally {
    loading.value = false
  }
}

async function addCompetitor() {
  try {
    await competitorsApi.add(websiteId, { name: newName.value, competitor_url: newUrl.value })
    showAdd.value = false
    newName.value = ''
    newUrl.value = ''
    await fetchData()
  } catch {}
}

onMounted(fetchData)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }

.changes-list { display: flex; flex-direction: column; gap: 12px; }
.change-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border-color); }
.change-item:last-child { border-bottom: none; }

.opp-bar { width: 100px; height: 6px; background: var(--bg-input); border-radius: var(--radius-full); overflow: hidden; }
.opp-fill { height: 100%; background: var(--color-success); border-radius: var(--radius-full); }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal-card {
  background: var(--bg-card); padding: 28px; border-radius: var(--radius-lg); width: 100%; max-width: 420px; box-shadow: var(--shadow-lg);
}
</style>
