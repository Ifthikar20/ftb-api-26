<template>
  <div class="audits-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">SEO Grader</h1>
        <p class="page-subtitle">See full report — per-page SEO analysis with suggested fixes.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="runAudit" :disabled="running">
        <svg v-if="!running" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        {{ running ? 'Scanning...' : 'Run Audit' }}
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading SEO grader data...</p>
    </div>

    <template v-else-if="grader">
      <!-- Score + Stats Row -->
      <div class="grader-top">
        <div class="score-ring-card card">
          <div class="score-ring" :class="scoreClass">
            <svg viewBox="0 0 120 120" class="ring-svg">
              <circle cx="60" cy="60" r="52" class="ring-bg"/>
              <circle cx="60" cy="60" r="52" class="ring-fill" :style="ringStyle"/>
            </svg>
            <div class="ring-label">
              <span class="ring-value">{{ grader.score }}</span>
              <span class="ring-max">/ 100</span>
            </div>
          </div>
          <div class="score-title">SEO Health Score</div>
        </div>

        <div class="stats-row">
          <div class="stat-block">
            <div class="stat-number">{{ grader.total_issues }}</div>
            <div class="stat-desc">Total issues found</div>
          </div>
          <div class="stat-block stat-red">
            <div class="stat-number">{{ grader.not_deployed }}</div>
            <div class="stat-desc">Not deployed</div>
          </div>
          <div class="stat-block stat-green">
            <div class="stat-number">{{ grader.deployed }}</div>
            <div class="stat-desc">Deployed</div>
          </div>
          <div class="stat-block">
            <div class="stat-number">{{ grader.flawless_pages }} / {{ grader.total_pages }}</div>
            <div class="stat-desc">Flawless Pages</div>
          </div>
        </div>
      </div>

      <!-- Progress Bars -->
      <div class="progress-row">
        <div class="card progress-card">
          <div class="progress-label">Issues Fixed</div>
          <div class="progress-bar-wrap">
            <div class="progress-bar" :style="{ width: fixedPct + '%' }" :class="fixedPct > 50 ? 'bar-green' : 'bar-red'"></div>
          </div>
          <div class="progress-text">{{ grader.deployed }} / {{ grader.total_issues }} · {{ fixedPct }}% completion</div>
        </div>
      </div>

      <!-- Category List -->
      <div class="categories-section">
        <h3 class="section-title">Issues by category</h3>

        <div v-for="cat in categories" :key="cat.key" class="card category-card">
          <div class="cat-header" @click="toggleCategory(cat.key)">
            <div class="cat-icon">{{ categoryIcon(cat.key) }}</div>
            <div class="cat-name">{{ cat.label }}</div>
            <div class="cat-count">
              <span class="cat-deployed">{{ cat.deployed }}</span>/<span>{{ cat.total }}</span>
            </div>
            <button class="btn btn-secondary btn-xs cat-toggle">
              {{ expandedCat === cat.key ? 'Hide' : 'View tasks' }}
            </button>
          </div>

          <!-- Expanded: per-page table -->
          <div v-if="expandedCat === cat.key" class="cat-body">
            <div class="cat-filter-row">
              <input v-model="catSearch" class="form-input form-input-sm" placeholder="Search by Page URL" />
              <div class="filter-tabs">
                <button :class="{ active: catFilter === 'all' }" @click="catFilter = 'all'">All <span class="count">{{ cat.total }}</span></button>
                <button :class="{ active: catFilter === 'deployed' }" @click="catFilter = 'deployed'">Deployed <span class="count">{{ cat.deployed }}</span></button>
                <button :class="{ active: catFilter === 'not_deployed' }" @click="catFilter = 'not_deployed'">Not Deployed <span class="count">{{ cat.total - cat.deployed }}</span></button>
              </div>
            </div>

            <div class="issues-table">
              <div v-for="item in filteredItems(cat)" :key="item.id" class="issue-row">
                <button class="deploy-toggle" :class="{ deployed: item.deployed }" @click="toggleDeploy(item)" :disabled="deploying === item.id">
                  {{ item.deployed ? 'Deployed' : 'Enable' }}
                </button>
                <div class="issue-url">{{ item.page_url }}</div>
                <div class="issue-values">
                  <div class="val-block original">
                    <div class="val-label">ORIGINAL</div>
                    <div class="val-meta">Length: {{ item.original_length }}</div>
                    <div class="val-text">{{ item.original_value || '—' }}</div>
                  </div>
                  <div class="val-block suggested" v-if="item.suggested_fix">
                    <div class="val-label">SUGGESTED FIX</div>
                    <div class="val-meta">Length: {{ item.suggested_length }}</div>
                    <div class="val-text">{{ item.suggested_fix }}</div>
                  </div>
                </div>
              </div>
              <div v-if="filteredItems(cat).length === 0" class="empty-filter">No items match this filter.</div>
            </div>

            <div class="pagination-info" v-if="cat.items.length > 0">
              Total records: {{ cat.total }}
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="empty-grader card">
        <div class="empty-icon">🔍</div>
        <h3>No SEO Grader Data</h3>
        <p>Run an audit to scan your site page-by-page and get category-based SEO fixes with deploy toggles.</p>
        <button class="btn btn-primary" @click="runAudit" :disabled="running">{{ running ? 'Scanning...' : 'Run Audit' }}</button>
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
const grader = ref(null)
const categories = ref([])
const expandedCat = ref(null)
const catSearch = ref('')
const catFilter = ref('all')
const deploying = ref(null)

const fixedPct = computed(() => {
  if (!grader.value || !grader.value.total_issues) return 0
  return Math.round((grader.value.deployed / grader.value.total_issues) * 100)
})

const scoreClass = computed(() => {
  if (!grader.value) return ''
  if (grader.value.score >= 80) return 'score-good'
  if (grader.value.score >= 50) return 'score-ok'
  return 'score-bad'
})

const ringStyle = computed(() => {
  const pct = grader.value?.score || 0
  const circumference = 2 * Math.PI * 52
  const offset = circumference - (pct / 100) * circumference
  return { strokeDasharray: circumference, strokeDashoffset: offset }
})

function categoryIcon(key) {
  const icons = {
    page_title: '📄', meta_description: '📝', image_alt: '🖼️',
    h1_length: 'H1', h2_length: 'H2', heading_optimization: '📐',
    canonical_link: '🔗', og_title: '📣', og_description: '📣', og_url: '🌐',
    twitter_title: '🐦', twitter_description: '🐦', twitter_site: '🐦', twitter_card: '🐦',
    lang_missing: '🌍', meta_keywords: '🔑', internal_linking: '🔗',
    organization_schema: '🏢', missing_keywords: '❓', link_issues: '⚠️',
  }
  return icons[key] || '📋'
}

function toggleCategory(key) {
  catSearch.value = ''
  catFilter.value = 'all'
  expandedCat.value = expandedCat.value === key ? null : key
}

function filteredItems(cat) {
  let items = cat.items
  if (catFilter.value === 'deployed') items = items.filter(i => i.deployed)
  if (catFilter.value === 'not_deployed') items = items.filter(i => !i.deployed)
  if (catSearch.value) {
    const q = catSearch.value.toLowerCase()
    items = items.filter(i => i.page_url.toLowerCase().includes(q))
  }
  return items
}

async function toggleDeploy(item) {
  deploying.value = item.id
  try {
    const { data } = await auditsApi.graderDeploy(websiteId, item.id)
    item.deployed = data.deployed
    // Update counts
    const cat = categories.value.find(c => c.items.includes(item))
    if (cat) cat.deployed = cat.items.filter(i => i.deployed).length
    grader.value.deployed = categories.value.reduce((s, c) => s + c.deployed, 0)
    grader.value.not_deployed = grader.value.total_issues - grader.value.deployed
  } catch (e) { console.error('Deploy failed', e) }
  finally { deploying.value = null }
}

async function fetchGrader() {
  loading.value = true
  try {
    const { data } = await auditsApi.grader(websiteId)
    grader.value = data.grader
    categories.value = data.categories || []
  } catch (e) { console.error('Grader fetch error', e) }
  finally { loading.value = false }
}

async function runAudit() {
  running.value = true
  try {
    await auditsApi.run(websiteId)
    // Poll for completion
    const poll = setInterval(async () => {
      try {
        const { data } = await auditsApi.status(websiteId)
        if (!data.running) {
          clearInterval(poll)
          running.value = false
          await fetchGrader()
        }
      } catch { clearInterval(poll); running.value = false }
    }, 3000)
  } catch { running.value = false }
}

onMounted(fetchGrader)
</script>

<style scoped>
/* ── Loading ── */
.loading-state { text-align: center; padding: 80px 20px; color: var(--text-muted); }
.spinner { width: 32px; height: 32px; border: 3px solid var(--border-color); border-top-color: var(--brand); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 12px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Score + Stats ── */
.grader-top { display: grid; grid-template-columns: auto 1fr; gap: 20px; margin-bottom: 20px; }
.score-ring-card { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 32px; }
.score-ring { position: relative; width: 120px; height: 120px; }
.ring-svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: var(--border-color); stroke-width: 8; }
.ring-fill { fill: none; stroke-width: 8; stroke-linecap: round; transition: stroke-dashoffset 0.8s ease; }
.score-good .ring-fill { stroke: var(--color-success, #22c55e); }
.score-ok .ring-fill { stroke: var(--color-warning, #f59e0b); }
.score-bad .ring-fill { stroke: var(--color-danger, #ef4444); }
.ring-label { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ring-value { font-size: 28px; font-weight: 700; line-height: 1; }
.ring-max { font-size: 12px; color: var(--text-muted); }
.score-title { font-size: 13px; color: var(--text-secondary); margin-top: 8px; font-weight: 600; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-block { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px 16px; text-align: center; }
.stat-number { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.stat-desc { font-size: 12px; color: var(--text-muted); }
.stat-red .stat-number { color: var(--color-danger, #ef4444); }
.stat-green .stat-number { color: var(--color-success, #22c55e); }

/* ── Progress ── */
.progress-row { margin-bottom: 24px; }
.progress-card { padding: 16px 20px; }
.progress-label { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.progress-bar-wrap { height: 8px; background: var(--border-color); border-radius: 4px; overflow: hidden; }
.progress-bar { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.bar-green { background: var(--color-success, #22c55e); }
.bar-red { background: var(--color-danger, #ef4444); }
.progress-text { font-size: 12px; color: var(--text-muted); margin-top: 6px; }

/* ── Categories ── */
.section-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.category-card { margin-bottom: 8px; overflow: hidden; }
.cat-header { display: flex; align-items: center; gap: 12px; padding: 14px 18px; cursor: pointer; transition: background 0.15s; }
.cat-header:hover { background: var(--bg-surface, rgba(0,0,0,0.02)); }
.cat-icon { font-size: 18px; width: 28px; text-align: center; flex-shrink: 0; }
.cat-name { font-weight: 600; font-size: 14px; flex: 1; }
.cat-count { font-size: 13px; color: var(--text-muted); font-weight: 600; }
.cat-count .cat-deployed { color: var(--color-success, #22c55e); }
.cat-toggle { flex-shrink: 0; }
.btn-xs { padding: 4px 10px; font-size: 11px; }

/* ── Expanded Category ── */
.cat-body { border-top: 1px solid var(--border-color); padding: 16px 18px; }
.cat-filter-row { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.cat-filter-row .form-input-sm { max-width: 240px; padding: 6px 10px; font-size: 12px; }
.filter-tabs { display: flex; gap: 4px; }
.filter-tabs button { padding: 4px 10px; font-size: 11px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: transparent; color: var(--text-secondary); cursor: pointer; transition: all 0.15s; }
.filter-tabs button.active { background: var(--brand); color: white; border-color: var(--brand); }
.filter-tabs .count { opacity: 0.7; margin-left: 2px; }

/* ── Issue Rows ── */
.issue-row { display: grid; grid-template-columns: 80px 1fr 2fr; gap: 12px; align-items: start; padding: 12px 0; border-bottom: 1px solid var(--border-color); }
.issue-row:last-child { border-bottom: none; }
.deploy-toggle { padding: 5px 12px; font-size: 11px; font-weight: 600; border-radius: var(--radius-md); cursor: pointer; border: 1px solid var(--border-color); background: var(--bg-card); color: var(--text-secondary); transition: all 0.15s; white-space: nowrap; }
.deploy-toggle:hover { border-color: var(--brand); color: var(--brand); }
.deploy-toggle.deployed { background: var(--color-success, #22c55e); color: white; border-color: var(--color-success, #22c55e); }
.issue-url { font-size: 12px; font-weight: 600; color: var(--text-primary); word-break: break-all; padding-top: 4px; }
.issue-values { display: flex; gap: 16px; }
.val-block { flex: 1; }
.val-label { font-size: 10px; font-weight: 700; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 2px; }
.val-meta { font-size: 10px; color: var(--text-muted); margin-bottom: 2px; }
.val-text { font-size: 12px; line-height: 1.4; color: var(--text-primary); }
.original .val-label { color: var(--text-muted); }
.suggested .val-label { color: var(--color-success, #22c55e); }
.suggested .val-text { color: var(--color-success, #22c55e); }

.empty-filter { text-align: center; padding: 20px; color: var(--text-muted); font-size: 13px; }
.pagination-info { font-size: 11px; color: var(--text-muted); margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color); }

/* ── Empty State ── */
.empty-grader { text-align: center; padding: 60px 20px; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-grader h3 { font-size: 18px; margin-bottom: 8px; }
.empty-grader p { color: var(--text-muted); font-size: 13px; margin-bottom: 20px; max-width: 400px; margin-left: auto; margin-right: auto; }

/* ── Responsive ── */
@media (max-width: 900px) {
  .grader-top { grid-template-columns: 1fr; }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .issue-row { grid-template-columns: 1fr; gap: 8px; }
  .issue-values { flex-direction: column; }
}
</style>
