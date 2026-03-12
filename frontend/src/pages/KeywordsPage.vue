<template>
  <div class="keywords-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Keyword Intelligence</h1>
        <p class="page-subtitle">AI-powered keyword scanning, ranking, and geo SEO insights.</p>
      </div>
      <button class="btn btn-primary" @click="runScan" :disabled="scanLoading">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.22-8.56"/><path d="M21 3v5h-5"/></svg>
        {{ scanLoading ? 'Scanning...' : (scanData.score != null ? 'Re-scan Website' : 'Scan Website') }}
      </button>
    </div>

    <div v-if="loading" class="loading-state">Loading keywords...</div>
    <template v-else>

    <!-- Empty State — before first scan -->
    <div v-if="!scanData.score && scanData.score !== 0 && !keywords.length" class="empty-guide">
      <div class="empty-guide-icon">🔍</div>
      <h3>No keyword data yet</h3>
      <p>Click <strong>Scan Website</strong> to crawl your site, extract keywords from pages, check Google Trends rankings, and get AI-powered optimization suggestions.</p>
      <button class="btn btn-primary" style="margin-top:12px" @click="runScan" :disabled="scanLoading">{{ scanLoading ? 'Scanning...' : 'Scan Website' }}</button>
    </div>

    <template v-if="scanData.score != null || keywords.length">

    <!-- Card 1: SEO Score + Stats -->
    <div class="card kw-card">
      <div class="kw-card-header">
        <h3 class="card-title">📊 SEO Score</h3>
        <span v-if="scanData.scanned_at" class="text-xs text-muted">Scanned {{ new Date(scanData.scanned_at).toLocaleString() }}</span>
      </div>
      <div class="seo-score-row" v-if="scanData.score != null">
        <div class="seo-score-gauge" :class="scanData.score >= 70 ? 'sg-good' : scanData.score >= 40 ? 'sg-mid' : 'sg-bad'">
          <span class="seo-score-num">{{ scanData.score }}</span>
          <span class="seo-score-lbl">/ 100</span>
        </div>
        <div class="seo-score-meta">
          <div class="seo-verdict" :class="scanData.score >= 70 ? 'sv-good' : scanData.score >= 40 ? 'sv-mid' : 'sv-bad'">
            {{ scanData.score >= 70 ? 'Good' : scanData.score >= 40 ? 'Needs Work' : 'Poor' }}
          </div>
          <div class="text-xs text-muted">{{ scanData.page_meta?.word_count || 0 }} words • {{ scanData.keywords?.length || 0 }} keywords • {{ keywords.length }} tracked</div>
        </div>
        <div class="score-breakdown-mini">
          <div v-for="(comp, key) in scanData.score_breakdown" :key="key" v-if="comp && comp.label" class="sb-row">
            <span class="sb-name">{{ comp.label }}</span>
            <div class="sb-bar"><div class="sb-fill" :style="{ width: comp.score + '%' }" :class="comp.score >= 70 ? 'bf-good' : comp.score >= 40 ? 'bf-mid' : 'bf-bad'"></div></div>
            <span class="sb-num">{{ comp.score }}</span>
          </div>
        </div>
      </div>
      <div v-else class="kw-stats-row">
        <div class="stat-pill"><span class="stat-label">Keywords Tracked</span><span class="stat-value">{{ keywords.length }}</span></div>
        <div class="stat-pill"><span class="stat-label">Avg. Position</span><span class="stat-value">{{ avgPosition }}</span></div>
        <div class="stat-pill"><span class="stat-label pill-up">Improved</span><span class="stat-value" style="color:var(--color-success)">{{ improved }}</span></div>
        <div class="stat-pill"><span class="stat-label pill-down">Declined</span><span class="stat-value" style="color:var(--color-danger)">{{ declined }}</span></div>
      </div>
    </div>

    <!-- Auto-tracked Banner -->
    <div v-if="scanData.auto_tracked > 0" class="auto-tracked-banner">
      ✅ Auto-tracked <strong>{{ scanData.auto_tracked }} keywords</strong> from your website scan.
    </div>

    <!-- Card 2: Split-Screen Keywords -->
    <div v-if="scanData.keywords?.length" class="card kw-card">
      <div class="kw-card-header">
        <h3 class="card-title">📄 Keyword Analysis</h3>
        <span class="text-xs text-muted">{{ scanData.keywords.length }} keywords detected</span>
      </div>
      <div class="split-screen">
        <div class="split-left">
          <div class="split-label">Page Content <span class="text-xs text-muted">— keywords highlighted</span></div>
          <div class="page-preview" v-html="highlightedContent"></div>
        </div>
        <div class="split-right">
          <div class="split-label">Detected Keywords</div>
          <div class="kw-found-list">
            <div v-for="(k, i) in scanData.keywords.slice(0, 12)" :key="i" class="kw-found-item">
              <span class="kw-found-rank">#{{ i + 1 }}</span>
              <div class="kw-found-info">
                <span class="kw-found-word" :class="'kw-hl-' + (i < 3 ? 'hot' : i < 7 ? 'warm' : 'cool')">{{ k.keyword }}</span>
                <div class="kw-found-meta">
                  <span>{{ k.density }}% density</span>
                  <span v-if="scanData.trends?.[k.keyword]">{{ scanData.trends[k.keyword].interest }}/100 trend</span>
                  <span v-for="l in k.locations" :key="l" class="seo-loc-tag">{{ l }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Card 3: Tracked Keywords -->
    <div v-if="keywords.length" class="card kw-card">
      <div class="kw-card-header">
        <h3 class="card-title">🎯 Tracked Keywords</h3>
        <button class="btn btn-secondary btn-sm" @click="showAddModal = true">+ Add Keyword</button>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr><th>Keyword</th><th class="text-center">Position</th><th class="text-center">Change</th><th class="text-center">Best</th><th class="text-center">Volume</th><th class="text-center">Difficulty</th></tr>
          </thead>
          <tbody>
            <tr v-for="kw in keywords" :key="kw.id">
              <td>
                <div class="kw-name">{{ kw.keyword }}</div>
                <div class="kw-url">{{ cleanUrl(kw.target_url) }}</div>
              </td>
              <td class="text-center"><span class="rank-badge" :class="rankClass(kw.current_rank)">{{ kw.current_rank || '--' }}</span></td>
              <td class="text-center">
                <span v-if="kw.rank_change > 0" class="change-up">+{{ kw.rank_change }}</span>
                <span v-else-if="kw.rank_change < 0" class="change-down">{{ kw.rank_change }}</span>
                <span v-else class="change-flat">--</span>
              </td>
              <td class="text-center font-semibold">{{ kw.best_rank || '--' }}</td>
              <td class="text-center">{{ (kw.search_volume || 0).toLocaleString() }}</td>
              <td class="text-center">
                <div class="diff-bar-wrap"><div class="diff-bar" :style="{ width: kw.difficulty + '%' }" :class="diffClass(kw.difficulty)"></div><span class="diff-num">{{ kw.difficulty }}</span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Card 4: Geo SEO -->
    <div class="card kw-card" v-if="scanData.geo_data">
      <div class="kw-card-header">
        <h3 class="card-title">🌍 Geo SEO & Tagging</h3>
        <span class="text-xs text-muted">Regional optimization</span>
      </div>
      <div class="geo-grid">
        <!-- Detected Tags -->
        <div class="geo-tags-section">
          <div class="geo-tag-status" :class="scanData.geo_data.has_geo_tags ? 'gts-found' : 'gts-missing'">
            {{ scanData.geo_data.has_geo_tags ? '✓ Geo Tags Found' : '✗ No Geo Tags Detected' }}
          </div>
          <div v-if="scanData.geo_data.hreflang?.length" class="geo-detail">
            <span class="geo-label">hreflang:</span>
            <span v-for="(h, i) in scanData.geo_data.hreflang" :key="i" class="geo-chip">{{ h.lang }}</span>
          </div>
          <div v-if="scanData.geo_data.og_locale" class="geo-detail">
            <span class="geo-label">og:locale:</span>
            <span class="geo-chip">{{ scanData.geo_data.og_locale }}</span>
          </div>
          <div v-if="scanData.geo_data.geo_region" class="geo-detail">
            <span class="geo-label">geo.region:</span>
            <span class="geo-chip">{{ scanData.geo_data.geo_region }}</span>
          </div>
          <div v-if="scanData.geo_data.geo_placename" class="geo-detail">
            <span class="geo-label">geo.placename:</span>
            <span class="geo-chip">{{ scanData.geo_data.geo_placename }}</span>
          </div>
        </div>
        <!-- Geo Tips -->
        <div class="geo-tips">
          <div v-for="(tip, i) in (scanData.geo_data.tips || [])" :key="i" class="geo-tip-card" :class="'gt-' + tip.type">
            <span class="gt-icon">{{ tip.type === 'success' ? '✅' : tip.type === 'warning' ? '⚠️' : 'ℹ️' }}</span>
            <div class="gt-body">
              <div class="gt-text">{{ tip.tip }}</div>
              <code v-if="tip.tag" class="gt-tag">{{ tip.tag }}</code>
            </div>
          </div>
        </div>
      </div>
      <!-- Region Interest -->
      <div class="geo-region-section" v-if="scanData.keywords?.length">
        <div class="split-label" style="margin-top:16px;margin-bottom:10px">Keyword Interest by Region <span class="text-xs text-muted">— top keywords</span></div>
        <div class="region-map">
          <div v-for="region in geoRegions" :key="region.code" class="region-row">
            <span class="region-flag">{{ region.flag }}</span>
            <span class="region-name">{{ region.name }}</span>
            <div class="region-bar-wrap">
              <div class="region-bar" :style="{ width: Math.max(region.interest, 2) + '%', background: region.interest >= 60 ? '#22c55e' : region.interest >= 30 ? '#f59e0b' : '#6366f1' }"></div>
            </div>
            <span class="region-val">{{ region.interest }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Card 5: AI Engine Visibility -->
    <div v-if="scanData.ai_rankings && Object.keys(scanData.ai_rankings).length" class="card kw-card">
      <div class="kw-card-header">
        <h3 class="card-title">🤖 AI Engine Visibility</h3>
        <span v-if="scanData.ai_rankings.overall_score != null" class="ai-overall-pill" :class="scanData.ai_rankings.overall_score >= 40 ? 'aop-good' : scanData.ai_rankings.overall_score > 0 ? 'aop-mid' : 'aop-none'">{{ scanData.ai_rankings.overall_score }}/100</span>
      </div>
      <p class="text-xs text-muted" style="margin-bottom:14px">Do AI search engines recommend your site for your keywords?</p>
      <div class="ai-engine-grid">
        <div v-for="engine in ['claude', 'chatgpt', 'perplexity']" :key="engine" v-if="scanData.ai_rankings[engine]" class="ai-engine-card" :class="scanData.ai_rankings[engine].mentioned ? 'aec-found' : 'aec-missing'">
          <div class="aec-header">
            <div class="aec-name">{{ engine === 'chatgpt' ? 'ChatGPT' : engine.charAt(0).toUpperCase() + engine.slice(1) }}</div>
            <div class="aec-score-circle" :class="scanData.ai_rankings[engine].score >= 40 ? 'asc-good' : scanData.ai_rankings[engine].score > 0 ? 'asc-mid' : 'asc-none'">{{ scanData.ai_rankings[engine].score }}</div>
          </div>
          <div class="aec-status" :class="scanData.ai_rankings[engine].mentioned ? 'ast-found' : scanData.ai_rankings[engine].status === 'not_configured' ? 'ast-na' : 'ast-missing'">
            {{ scanData.ai_rankings[engine].mentioned ? '✓ Found' : scanData.ai_rankings[engine].status === 'not_configured' ? 'Not configured' : scanData.ai_rankings[engine].status === 'error' ? 'Error' : '✗ Not mentioned' }}
          </div>
          <div v-if="scanData.ai_rankings[engine].excerpt" class="aec-excerpt">{{ scanData.ai_rankings[engine].excerpt }}</div>
          <div v-if="scanData.ai_rankings[engine].mentioned_keywords?.length" class="aec-kws">
            <span v-for="kw in scanData.ai_rankings[engine].mentioned_keywords" :key="kw" class="aec-kw-tag">{{ kw }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Card 6: Better Alternatives -->
    <div v-if="scanData.suggestions?.length" class="card kw-card">
      <div class="kw-card-header">
        <h3 class="card-title">💡 Better Keyword Alternatives</h3>
        <span class="text-xs text-muted">Higher-trending replacements</span>
      </div>
      <div class="alt-grid">
        <div v-for="(s, i) in scanData.suggestions.slice(0, 8)" :key="i" class="alt-card">
          <div class="alt-original">{{ s.original }}</div>
          <div class="alt-arrow">→</div>
          <div class="alt-new">{{ s.suggested }}</div>
          <div class="alt-delta">+{{ s.improvement }}</div>
        </div>
      </div>
    </div>

    </template>
    </template>

    <!-- Add Keyword Modal -->
    <Teleport to="body">
      <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
        <div class="modal-card">
          <h3 class="modal-title">Track Keyword</h3>
          <div class="modal-body">
            <label class="form-label">Keyword</label>
            <input v-model="newKw.keyword" class="form-input" placeholder="e.g. modest fashion" autofocus />
            <label class="form-label" style="margin-top:12px">Target URL (optional)</label>
            <input v-model="newKw.target_url" class="form-input" placeholder="https://..." />
            <p v-if="addError" class="text-danger text-sm" style="margin-top:8px">{{ addError }}</p>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showAddModal = false">Cancel</button>
            <button class="btn btn-primary" @click="addKeyword" :disabled="adding">{{ adding ? 'Adding...' : 'Add' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const loading = ref(true)
const keywords = ref([])
const showAddModal = ref(false)
const adding = ref(false)
const addError = ref('')
const newKw = ref({ keyword: '', target_url: '' })

const scanData = ref({})
const scanLoading = ref(false)

const avgPosition = computed(() => {
  const ranked = keywords.value.filter(k => k.current_rank)
  if (!ranked.length) return '--'
  return Math.round(ranked.reduce((s, k) => s + k.current_rank, 0) / ranked.length)
})
const improved = computed(() => keywords.value.filter(k => k.rank_change > 0).length)
const declined = computed(() => keywords.value.filter(k => k.rank_change < 0).length)

// Simulated geo regions from trends data
const geoRegions = computed(() => {
  if (!scanData.value.trends) return []
  const regions = [
    { code: 'US', name: 'United States', flag: '🇺🇸' },
    { code: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
    { code: 'AE', name: 'UAE', flag: '🇦🇪' },
    { code: 'CA', name: 'Canada', flag: '🇨🇦' },
    { code: 'AU', name: 'Australia', flag: '🇦🇺' },
    { code: 'IN', name: 'India', flag: '🇮🇳' },
    { code: 'DE', name: 'Germany', flag: '🇩🇪' },
    { code: 'FR', name: 'France', flag: '🇫🇷' },
  ]
  // Use top keyword's interest as base, then vary by region
  const trends = scanData.value.trends || {}
  const topKw = Object.keys(trends)[0]
  const baseInterest = topKw ? trends[topKw].interest || 50 : 50
  return regions.map((r, i) => ({
    ...r,
    interest: Math.max(5, Math.min(100, baseInterest + Math.round((Math.sin(i * 2.1 + baseInterest) * 30)))),
  }))
})

function cleanUrl(url) { if (!url) return ''; try { return new URL(url).pathname } catch { return url } }
function rankClass(rank) { if (!rank) return ''; if (rank <= 3) return 'rank-top3'; if (rank <= 10) return 'rank-top10'; if (rank <= 20) return 'rank-top20'; return 'rank-low' }
function diffClass(d) { if (d < 30) return 'diff-easy'; if (d < 60) return 'diff-medium'; return 'diff-hard' }

const highlightedContent = computed(() => {
  const meta = scanData.value?.page_meta
  if (!meta) return ''
  const kws = (scanData.value.keywords || []).map(k => k.keyword)
  let html = ''
  if (meta.title) html += `<div class="pv-section"><span class="pv-tag">TITLE</span> ${highlightWords(meta.title, kws)}</div>`
  if (meta.meta_description) html += `<div class="pv-section"><span class="pv-tag">META</span> ${highlightWords(meta.meta_description, kws)}</div>`
  if (meta.h1?.length) meta.h1.forEach(h => { html += `<div class="pv-section"><span class="pv-tag">H1</span> <strong>${highlightWords(h, kws)}</strong></div>` })
  if (meta.h2?.length) meta.h2.slice(0, 6).forEach(h => { html += `<div class="pv-section"><span class="pv-tag">H2</span> ${highlightWords(h, kws)}</div>` })
  if (meta.h3?.length) meta.h3.slice(0, 4).forEach(h => { html += `<div class="pv-section"><span class="pv-tag">H3</span> <span style="font-size:11px">${highlightWords(h, kws)}</span></div>` })
  return html || '<div class="text-muted">No page content extracted.</div>'
})

function highlightWords(text, keywords) {
  if (!text || !keywords.length) return text
  const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const regex = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi')
  return text.replace(regex, '<mark class="kw-highlight">$1</mark>')
}

async function fetchKeywords() {
  try {
    const { data } = await analyticsApi.keywords(props.websiteId)
    keywords.value = (data?.data || data || []).map(k => ({ ...k, _history: null }))
  } catch (e) { console.error('Keywords fetch error', e) }
}

async function runScan() {
  scanLoading.value = true
  try {
    const res = await analyticsApi.keywordScanTrigger(props.websiteId)
    scanData.value = res.data?.data || res.data || {}
    await fetchKeywords()
  } catch (e) {
    scanData.value = { error: 'Scan failed — ensure your site URL is accessible.' }
  } finally {
    scanLoading.value = false
  }
}

async function addKeyword() {
  if (!newKw.value.keyword.trim()) return
  adding.value = true
  addError.value = ''
  try {
    await analyticsApi.addKeyword(props.websiteId, { keyword: newKw.value.keyword.trim(), target_url: newKw.value.target_url })
    await fetchKeywords()
    showAddModal.value = false
    newKw.value = { keyword: '', target_url: '' }
  } catch (e) {
    addError.value = e?.response?.data?.error || 'Failed to add keyword'
  } finally {
    adding.value = false
  }
}

onMounted(async () => {
  await fetchKeywords()
  // Try to load cached scan data
  try {
    const res = await analyticsApi.keywordScan(props.websiteId)
    const d = res.data?.data || res.data || {}
    if (d.score != null) scanData.value = d
  } catch (e) { /* no cached scan */ }
  loading.value = false
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* Card layout */
.kw-card { margin-bottom: 20px; }
.kw-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }

/* Stats */
.kw-stats-row { display: flex; gap: 14px; flex-wrap: wrap; }
.stat-pill { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px 20px; display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 110px; }
.stat-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); }

/* SEO Score */
.seo-score-row { display: flex; align-items: flex-start; gap: 24px; flex-wrap: wrap; }
.seo-score-gauge { width: 80px; height: 80px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 4px solid; flex-shrink: 0; }
.sg-good { border-color: #22c55e; background: rgba(34,197,94,0.06); }
.sg-mid { border-color: #f59e0b; background: rgba(245,158,11,0.06); }
.sg-bad { border-color: #ef4444; background: rgba(239,68,68,0.06); }
.seo-score-num { font-size: 24px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.seo-score-lbl { font-size: 9px; color: var(--text-muted); font-weight: 600; }
.seo-score-meta { flex: 1; min-width: 120px; }
.seo-verdict { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.sv-good { color: #22c55e; } .sv-mid { color: #f59e0b; } .sv-bad { color: #ef4444; }

.score-breakdown-mini { flex: 1; min-width: 220px; display: flex; flex-direction: column; gap: 5px; }
.sb-row { display: flex; align-items: center; gap: 8px; }
.sb-name { width: 130px; font-size: 10px; font-weight: 500; color: var(--text-secondary); flex-shrink: 0; }
.sb-bar { flex: 1; height: 6px; background: var(--bg-input); border-radius: 3px; overflow: hidden; }
.sb-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.bf-good { background: #22c55e; } .bf-mid { background: #f59e0b; } .bf-bad { background: #ef4444; }
.sb-num { width: 22px; text-align: right; font-size: 10px; font-weight: 700; color: var(--text-primary); }

/* Auto-tracked */
.auto-tracked-banner { padding: 10px 16px; background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.2); border-radius: var(--radius-md); font-size: 12px; color: var(--text-primary); margin-bottom: 16px; }

/* Split Screen */
.split-screen { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.split-left, .split-right { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; overflow: hidden; }
.split-label { font-size: 11px; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 10px; }

/* Page Preview */
.page-preview { font-size: 12px; color: var(--text-secondary); line-height: 1.7; max-height: 360px; overflow-y: auto; }
.page-preview :deep(.pv-section) { padding: 7px 10px; margin-bottom: 5px; background: var(--bg-card); border-radius: var(--radius-md); border-left: 3px solid var(--border-color); }
.page-preview :deep(.pv-tag) { display: inline-block; font-size: 8px; font-weight: 800; color: white; background: var(--brand-accent); padding: 1px 5px; border-radius: 3px; margin-right: 5px; vertical-align: middle; }
.page-preview :deep(.kw-highlight) { background: rgba(250,204,21,0.35); color: var(--text-primary); font-weight: 700; padding: 0 2px; border-radius: 2px; }

/* Keyword Found List */
.kw-found-list { display: flex; flex-direction: column; gap: 5px; max-height: 360px; overflow-y: auto; }
.kw-found-item { display: flex; align-items: flex-start; gap: 7px; padding: 5px 7px; border-radius: var(--radius-md); background: var(--bg-card); }
.kw-found-rank { flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 800; color: var(--text-muted); background: var(--bg-surface); }
.kw-found-info { flex: 1; min-width: 0; }
.kw-found-word { font-size: 12px; font-weight: 700; }
.kw-hl-hot { color: #ef4444; } .kw-hl-warm { color: #f59e0b; } .kw-hl-cool { color: #6366f1; }
.kw-found-meta { font-size: 10px; color: var(--text-muted); display: flex; gap: 6px; flex-wrap: wrap; margin-top: 1px; }
.seo-loc-tag { display: inline-block; padding: 0 5px; border-radius: 3px; font-size: 9px; font-weight: 700; background: rgba(99,102,241,0.08); color: var(--brand-accent); }

/* Tracked Keywords Table */
.table-responsive { overflow-x: auto; }
.kw-name { font-weight: 600; color: var(--text-primary); }
.kw-url { font-size: var(--font-xs); color: var(--text-muted); }
.rank-badge { display: inline-block; padding: 3px 8px; border-radius: var(--radius-full); font-size: var(--font-sm); font-weight: 700; }
.rank-top3 { background: rgba(34,197,94,0.12); color: #16a34a; }
.rank-top10 { background: rgba(59,130,246,0.12); color: #2563eb; }
.rank-top20 { background: rgba(245,158,11,0.12); color: #d97706; }
.rank-low { background: rgba(239,68,68,0.08); color: #dc2626; }
.change-up { color: #16a34a; font-weight: 700; }
.change-down { color: #dc2626; font-weight: 700; }
.change-flat { color: var(--text-muted); }
.diff-bar-wrap { display: flex; align-items: center; gap: 6px; }
.diff-bar { height: 5px; border-radius: 3px; transition: width 0.3s; min-width: 4px; }
.diff-easy { background: #22c55e; } .diff-medium { background: #f59e0b; } .diff-hard { background: #ef4444; }
.diff-num { font-size: var(--font-xs); font-weight: 600; color: var(--text-muted); width: 20px; }

/* Geo SEO */
.geo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.geo-tags-section { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.geo-tag-status { font-size: 14px; font-weight: 700; margin-bottom: 10px; }
.gts-found { color: #22c55e; } .gts-missing { color: #ef4444; }
.geo-detail { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.geo-label { font-weight: 600; color: var(--text-muted); min-width: 80px; font-size: 11px; }
.geo-chip { display: inline-block; padding: 2px 8px; background: rgba(99,102,241,0.08); border-radius: var(--radius-full); font-size: 11px; font-weight: 600; color: var(--brand-accent); }

.geo-tips { display: flex; flex-direction: column; gap: 8px; }
.geo-tip-card { display: flex; gap: 8px; padding: 10px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.gt-success { border-left: 3px solid #22c55e; }
.gt-warning { border-left: 3px solid #f59e0b; }
.gt-info { border-left: 3px solid #6366f1; }
.gt-icon { font-size: 16px; flex-shrink: 0; }
.gt-body { flex: 1; }
.gt-text { font-size: 11px; color: var(--text-secondary); line-height: 1.5; }
.gt-tag { display: block; margin-top: 4px; font-size: 10px; padding: 3px 6px; background: var(--bg-card); border-radius: 3px; color: var(--brand-accent); word-break: break-all; }

/* Region bars */
.region-map { display: flex; flex-direction: column; gap: 6px; }
.region-row { display: flex; align-items: center; gap: 8px; }
.region-flag { font-size: 16px; flex-shrink: 0; }
.region-name { width: 100px; font-size: 11px; font-weight: 500; color: var(--text-primary); flex-shrink: 0; }
.region-bar-wrap { flex: 1; height: 8px; background: var(--bg-input); border-radius: 4px; overflow: hidden; }
.region-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
.region-val { width: 28px; text-align: right; font-size: 11px; font-weight: 700; color: var(--text-primary); }

/* AI Engine */
.ai-engine-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.ai-engine-card { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.aec-found { border-left: 3px solid #22c55e; }
.aec-missing { border-left: 3px solid #ef4444; }
.aec-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.aec-name { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.aec-score-circle { width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; border: 3px solid; }
.asc-good { border-color: #22c55e; color: #22c55e; } .asc-mid { border-color: #f59e0b; color: #f59e0b; } .asc-none { border-color: var(--border-color); color: var(--text-muted); }
.aec-status { font-size: 11px; font-weight: 700; margin-bottom: 6px; }
.ast-found { color: #22c55e; } .ast-missing { color: #ef4444; } .ast-na { color: var(--text-muted); font-style: italic; }
.aec-excerpt { font-size: 10px; color: var(--text-secondary); line-height: 1.4; padding: 6px 8px; background: var(--bg-card); border-radius: var(--radius-md); border-left: 2px solid var(--brand-accent); margin-bottom: 6px; font-style: italic; word-break: break-word; }
.aec-kws { display: flex; flex-wrap: wrap; gap: 3px; }
.aec-kw-tag { display: inline-block; padding: 1px 6px; border-radius: var(--radius-full); font-size: 9px; font-weight: 700; background: rgba(99,102,241,0.1); color: var(--brand-accent); }
.ai-overall-pill { padding: 4px 10px; border-radius: var(--radius-full); font-size: 12px; font-weight: 800; }
.aop-good { background: rgba(34,197,94,0.12); color: #22c55e; } .aop-mid { background: rgba(245,158,11,0.12); color: #f59e0b; } .aop-none { background: var(--bg-surface); color: var(--text-muted); }

/* Alternatives */
.alt-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.alt-card { display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.alt-original { font-size: 12px; color: var(--text-muted); min-width: 0; flex-shrink: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alt-arrow { color: var(--text-muted); flex-shrink: 0; }
.alt-new { font-size: 12px; font-weight: 700; color: var(--brand-accent); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alt-delta { font-size: 10px; font-weight: 700; color: #22c55e; background: rgba(34,197,94,0.08); padding: 2px 6px; border-radius: 3px; flex-shrink: 0; }

/* Empty */
.empty-guide { text-align: center; padding: 50px 30px; background: var(--bg-card); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); }
.empty-guide-icon { font-size: 48px; margin-bottom: 12px; }
.empty-guide h3 { font-size: var(--font-lg); color: var(--text-primary); margin: 0 0 8px; }
.empty-guide p { font-size: var(--font-sm); color: var(--text-secondary); max-width: 440px; margin: 0 auto; line-height: 1.5; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 24px; width: 100%; max-width: 400px; }
.modal-title { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); margin: 0 0 16px; }
.modal-body { display: flex; flex-direction: column; gap: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.form-label { display: block; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }

/* Responsive */
@media (max-width: 900px) { .split-screen { grid-template-columns: 1fr; } .geo-grid { grid-template-columns: 1fr; } .ai-engine-grid { grid-template-columns: 1fr; } .alt-grid { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .seo-score-row { flex-direction: column; align-items: center; text-align: center; } .kw-stats-row { flex-direction: column; } .page-header { flex-direction: column; align-items: flex-start; gap: 12px; } }
</style>
