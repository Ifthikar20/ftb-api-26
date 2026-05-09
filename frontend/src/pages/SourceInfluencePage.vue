<template>
  <div class="si-page">
    <!-- Header -->
    <div id="si-header" class="si-header">
      <div class="si-title-block">
        <h1 class="si-title">Source Influence</h1>
        <p class="si-subtitle" v-if="websiteName">{{ websiteName }}</p>
      </div>
      <div id="si-controls" class="si-controls">
        <div class="si-segmented" role="group" aria-label="Period">
          <button
            v-for="opt in periodOptions"
            :key="opt.value"
            class="si-seg-btn"
            :class="{ active: periodDays === opt.value }"
            @click="periodDays = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
        <div class="si-segmented" role="group" aria-label="Provider">
          <button
            v-for="opt in providerOptions"
            :key="opt.value || 'all'"
            class="si-seg-btn"
            :class="{ active: providerFilter === opt.value }"
            @click="providerFilter = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="si-loading">Loading source influence…</div>

    <template v-else>
      <!-- Empty state -->
      <div v-if="totalCitations === 0" class="si-empty">
        <div class="si-empty-illus">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="40" cy="40" r="30" stroke-dasharray="4 4"/>
            <path d="M28 40h24M40 28v24" stroke-linecap="round"/>
          </svg>
        </div>
        <h2 class="si-empty-title">No citations yet</h2>
        <p class="si-empty-copy">
          Run an audit to start tracking which sources LLMs cite for your category.
        </p>
        <AirButton
          as="router-link"
          :to="`/llm-ranking/${websiteId}`"
          variant="primary"
          size="md"
        >
          Run new audit
        </AirButton>
      </div>

      <template v-else>
        <!-- Top stat row -->
        <div id="si-stats" class="si-stats">
          <div class="si-stat">
            <div class="si-stat-label">Total citations</div>
            <div class="si-stat-value">{{ totalCitations.toLocaleString() }}</div>
            <div class="si-stat-sub">over last {{ periodDays }} days</div>
          </div>
          <div class="si-stat">
            <div class="si-stat-label">Unique domains</div>
            <div class="si-stat-value">{{ uniqueDomains.toLocaleString() }}</div>
            <div class="si-stat-sub">distinct apex domains</div>
          </div>
          <div class="si-stat">
            <div class="si-stat-label">Your-site share</div>
            <div class="si-stat-value">{{ pct(yourSiteShare) }}<span class="si-stat-unit">%</span></div>
            <div class="si-stat-sub">{{ yourSiteCount }} citations</div>
          </div>
          <div class="si-stat">
            <div class="si-stat-label">Competitor share</div>
            <div class="si-stat-value">{{ pct(competitorShare) }}<span class="si-stat-unit">%</span></div>
            <div class="si-stat-sub">{{ competitorCount }} citations</div>
          </div>
        </div>

        <!-- Per-provider breakdown cards -->
        <div id="si-providers" class="si-section">
          <h2 class="si-section-title">Source mix by provider</h2>
          <div v-if="!providerCards.length" class="si-card si-empty-inline">
            No per-provider rollups for this window yet.
          </div>
          <div v-for="card in providerCards" :key="card.provider" class="si-card">
            <div class="si-card-head">
              <div>
                <div class="si-card-title">{{ providerLabel(card.provider) }}</div>
                <div class="si-card-sub">{{ card.total.toLocaleString() }} citations</div>
              </div>
              <button class="si-link-btn" @click="card.expanded = !card.expanded">
                {{ card.expanded ? 'Hide top domains' : 'View top domains' }}
              </button>
            </div>
            <SourceBreakdownBar :breakdown="card.breakdown" :height="14" />
            <p class="si-card-line" v-if="card.topClass">
              Top source: <strong>{{ titleCase(card.topClass.source_class) }}</strong>
              ({{ pct(card.topClass.share) }}%)
            </p>
            <div v-if="card.expanded" class="si-domains-mini">
              <table class="si-table">
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th class="num">Count</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in card.top_domains.slice(0, 10)" :key="d.apex_domain">
                    <td>{{ d.apex_domain }}</td>
                    <td class="num">{{ d.count }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Top domains table -->
        <div class="si-section">
          <h2 class="si-section-title">Top domains</h2>
          <div class="si-card">
            <table class="si-table">
              <thead>
                <tr>
                  <th @click="toggleSort('apex_domain')" class="sortable">
                    Domain
                    <span v-if="sortKey === 'apex_domain'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th @click="toggleSort('source_class')" class="sortable">
                    Source class
                    <span v-if="sortKey === 'source_class'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="num sortable" @click="toggleSort('count')">
                    Count
                    <span v-if="sortKey === 'count'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="num sortable" @click="toggleSort('share')">
                    Share
                    <span v-if="sortKey === 'share'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="sortable" @click="toggleSort('type')">
                    Type
                    <span v-if="sortKey === 'type'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in visibleDomains"
                  :key="row.apex_domain"
                  class="clickable"
                  @click="openDomainDrawer(row)"
                >
                  <td>{{ row.apex_domain }}</td>
                  <td>
                    <SourceClassBadge :source_class="row.source_class || 'other'" />
                  </td>
                  <td class="num">{{ row.count }}</td>
                  <td class="num">{{ pct(row.share) }}%</td>
                  <td>
                    <span v-if="row.is_target" class="si-pill si-pill-you">Your site</span>
                    <span v-else-if="row.is_competitor" class="si-pill si-pill-comp">Competitor</span>
                    <span v-else class="si-pill si-pill-other">Other</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="si-table-foot">
              <span class="si-muted">
                Showing {{ Math.min(visibleDomains.length, sortedDomains.length) }}
                of {{ sortedDomains.length }}
              </span>
              <button
                v-if="domainLimit < sortedDomains.length"
                class="si-link-btn"
                @click="domainLimit += 30"
              >
                Show more
              </button>
            </div>
          </div>
        </div>

        <!-- Recommendations -->
        <div id="si-recs" class="si-section">
          <h2 class="si-section-title">Recommendations</h2>
          <div class="si-recs">
            <div v-for="(rec, i) in recommendations" :key="i" class="si-rec-card">
              <div class="si-rec-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                  <circle cx="10" cy="10" r="8"/>
                  <path d="M10 6v5M10 13.5h.01" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="si-rec-body">
                <div class="si-rec-headline">{{ rec.headline }}</div>
                <p class="si-rec-desc" v-html="rec.description"></p>
                <AirButton
                  v-if="rec.cta"
                  variant="outline"
                  size="sm"
                  @click="rec.action && rec.action()"
                >
                  {{ rec.cta }}
                </AirButton>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>

    <CitationsDrawer
      v-model:open="drawerOpen"
      :citations="drawerCitations"
      :provider="drawerProvider"
      :prompt="drawerPrompt"
    />

    <OnboardingTooltip storage-key="fb_tour_source_influence_v1" :steps="tourSteps" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import citationsApi from '@/api/citations'
import SourceClassBadge from '@/components/citations/SourceClassBadge.vue'
import SourceBreakdownBar from '@/components/citations/SourceBreakdownBar.vue'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'
import AirButton from '@/components/ui/AirButton.vue'

const tourSteps = [
  {
    target: '#si-header',
    title: 'Source Influence',
    message: 'See which websites AI assistants pull from when answering questions about your category. Knowing this tells you where to invest content effort.',
    position: 'bottom',
  },
  {
    target: '#si-controls',
    title: 'Filter the view',
    message: 'Narrow by time period (7 / 30 / 90 days) or by AI provider. Each provider has its own citation pattern — Perplexity favors Reddit, Gemini leans on news, etc.',
    position: 'bottom',
  },
  {
    target: '#si-stats',
    title: 'Top-line metrics',
    message: 'Total citations and unique domains tell you the breadth. Your-site share vs competitor share is the headline number to move.',
    position: 'bottom',
  },
  {
    target: '#si-providers',
    title: 'Source mix per provider',
    message: 'Each card shows how a single LLM splits its citations across source classes. Click a card to see top domains for that provider.',
    position: 'top',
  },
  {
    target: '#si-recs',
    title: 'Actionable recommendations',
    message: 'These are auto-generated based on the gaps in your citation pattern — click through to act on them.',
    position: 'top',
  },
]
import CitationsDrawer from '@/components/citations/CitationsDrawer.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const websiteId = route.params.websiteId

const loading = ref(true)
const snapshots = ref([])
const recentCitations = ref([])

const periodDays = ref(30)
const providerFilter = ref('')

const periodOptions = [
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
]
const providerOptions = [
  { value: '', label: 'All' },
  { value: 'claude', label: 'Claude' },
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'perplexity', label: 'Perplexity' },
]

const websiteName = computed(() => appStore.activeWebsite?.name || '')

const drawerOpen = ref(false)
const drawerCitations = ref([])
const drawerProvider = ref('')
const drawerPrompt = ref('')

const sortKey = ref('count')
const sortDir = ref('desc')
const domainLimit = ref(30)

function pct(share) {
  return Math.round((share || 0) * 1000) / 10
}

function titleCase(v) {
  return (v || 'other')
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

function providerLabel(p) {
  if (!p) return 'All providers'
  const label = providerOptions.find((o) => o.value === p)
  if (label) return label.label
  return p
    .split(/[-_]/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

async function load() {
  loading.value = true
  try {
    const [siRes, citRes] = await Promise.all([
      citationsApi.websiteSourceInfluence(websiteId, {
        period_days: periodDays.value,
        ...(providerFilter.value ? { provider: providerFilter.value } : {}),
      }),
      citationsApi.websiteCitations(websiteId, {
        ...(providerFilter.value ? { provider: providerFilter.value } : {}),
      }),
    ])
    const siBody = siRes.data?.data || siRes.data || {}
    snapshots.value = siBody.snapshots || []

    const citBody = citRes.data?.data || citRes.data || {}
    recentCitations.value = citBody.results || citBody || []
  } catch (e) {
    console.error('Failed to load source influence', e)
    snapshots.value = []
    recentCitations.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch([periodDays, providerFilter], load)

// Aggregated breakdown across snapshots (since each snapshot is per-provider).
const aggregateBreakdown = computed(() => {
  const out = {}
  let total = 0
  for (const snap of snapshots.value) {
    for (const [cls, info] of Object.entries(snap.breakdown || {})) {
      if (!out[cls]) out[cls] = { count: 0, share: 0 }
      out[cls].count += info.count || 0
      total += info.count || 0
    }
  }
  if (total > 0) {
    for (const cls of Object.keys(out)) {
      out[cls].share = out[cls].count / total
    }
  }
  return { breakdown: out, total }
})

const totalCitations = computed(() =>
  snapshots.value.reduce((acc, s) => acc + (s.total_citations || 0), 0),
)

const aggregatedDomains = computed(() => {
  const map = new Map()
  for (const snap of snapshots.value) {
    for (const d of snap.top_domains || []) {
      const key = d.apex_domain
      if (!key) continue
      const existing = map.get(key) || { apex_domain: key, count: 0 }
      existing.count += d.count || 0
      map.set(key, existing)
    }
  }
  // Cross-reference with citation rows for is_target/is_competitor/source_class.
  const meta = new Map()
  for (const c of recentCitations.value) {
    const key = c.apex_domain
    if (!key) continue
    if (!meta.has(key)) {
      meta.set(key, {
        is_target: !!c.is_target,
        is_competitor: !!c.is_competitor,
        source_class: c.source_class,
      })
    }
  }
  const list = []
  let grand = 0
  for (const row of map.values()) {
    grand += row.count
    list.push(row)
  }
  return list.map((row) => {
    const m = meta.get(row.apex_domain) || {}
    return {
      ...row,
      share: grand > 0 ? row.count / grand : 0,
      is_target: m.is_target || false,
      is_competitor: m.is_competitor || false,
      source_class: m.source_class || 'other',
    }
  })
})

const uniqueDomains = computed(() => aggregatedDomains.value.length)

const yourSiteCount = computed(() => {
  const b = aggregateBreakdown.value.breakdown
  return b.your_site?.count || 0
})
const yourSiteShare = computed(() => {
  const b = aggregateBreakdown.value.breakdown
  return b.your_site?.share || 0
})
const competitorCount = computed(() => {
  const b = aggregateBreakdown.value.breakdown
  return b.competitor_site?.count || 0
})
const competitorShare = computed(() => {
  const b = aggregateBreakdown.value.breakdown
  return b.competitor_site?.share || 0
})

const providerCards = computed(() => {
  const grouped = new Map()
  for (const snap of snapshots.value) {
    if (!snap.provider) continue
    const existing = grouped.get(snap.provider) || {
      provider: snap.provider,
      total: 0,
      breakdown: {},
      top_domains: [],
      expanded: false,
    }
    existing.total += snap.total_citations || 0
    for (const [cls, info] of Object.entries(snap.breakdown || {})) {
      if (!existing.breakdown[cls]) existing.breakdown[cls] = { count: 0, share: 0 }
      existing.breakdown[cls].count += info.count || 0
    }
    for (const d of snap.top_domains || []) {
      const found = existing.top_domains.find((x) => x.apex_domain === d.apex_domain)
      if (found) found.count += d.count
      else existing.top_domains.push({ ...d })
    }
    grouped.set(snap.provider, existing)
  }
  for (const card of grouped.values()) {
    const totalForCard = Object.values(card.breakdown).reduce((acc, v) => acc + v.count, 0)
    if (totalForCard > 0) {
      for (const cls of Object.keys(card.breakdown)) {
        card.breakdown[cls].share = card.breakdown[cls].count / totalForCard
      }
    }
    card.top_domains.sort((a, b) => b.count - a.count)
    let topClass = null
    for (const [cls, info] of Object.entries(card.breakdown)) {
      if (!topClass || info.count > topClass.count) {
        topClass = { source_class: cls, ...info }
      }
    }
    card.topClass = topClass
  }
  return Array.from(grouped.values()).sort((a, b) => b.total - a.total)
})

const domainSort = computed({
  get: () => ({ key: sortKey.value, dir: sortDir.value }),
  set: (v) => {
    sortKey.value = v.key
    sortDir.value = v.dir
  },
})

function _typeRank(row) {
  if (row.is_target) return 0
  if (row.is_competitor) return 1
  return 2
}

const sortedDomains = computed(() => {
  const dir = sortDir.value === 'asc' ? 1 : -1
  const key = sortKey.value
  const list = [...aggregatedDomains.value]
  return list.sort((a, b) => {
    let av
    let bv
    if (key === 'type') {
      av = _typeRank(a)
      bv = _typeRank(b)
    } else {
      av = a[key] ?? ''
      bv = b[key] ?? ''
    }
    if (typeof av === 'number' && typeof bv === 'number') {
      return (av - bv) * dir
    }
    return String(av).localeCompare(String(bv)) * dir
  })
})

const visibleDomains = computed(() => sortedDomains.value.slice(0, domainLimit.value))

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc'
  }
}

function openDomainDrawer(row) {
  const matching = recentCitations.value.filter((c) => c.apex_domain === row.apex_domain)
  drawerCitations.value = matching
  drawerProvider.value = providerFilter.value || 'All providers'
  drawerPrompt.value = `Citations from ${row.apex_domain}`
  drawerOpen.value = true
}

const recommendations = computed(() => {
  const recs = []
  const b = aggregateBreakdown.value.breakdown
  const yShare = yourSiteShare.value
  const cShare = competitorShare.value
  const blogShare = b.blog?.share || 0
  const redditShare = b.reddit?.share || 0
  // Approximate "your-site reddit citations" by looking at recent citations.
  const yourSiteRedditCount = recentCitations.value.filter(
    (c) => c.is_target && c.source_class === 'reddit',
  ).length

  if (yShare < 0.05 && blogShare > 0.15) {
    recs.push({
      headline: 'You are rarely cited from blog content',
      description:
        '<strong>Publish more long-form articles</strong> targeting questions in your category to claim a share of blog citations.',
      cta: 'Open prompt library',
      action: () => router.push(`/llm-ranking/${websiteId}/prompts`),
    })
  }
  if (redditShare > 0.2 && yourSiteRedditCount === 0) {
    recs.push({
      headline: `Reddit drives ${pct(redditShare)}% of citations in your category`,
      description:
        '<strong>Engage with the top threads</strong> where LLMs source community signal.',
      cta: 'View Reddit citations',
      action: () => filterByClass('reddit'),
    })
  }
  if (cShare / Math.max(yShare, 0.001) > 3) {
    recs.push({
      headline: 'Competitors are cited far more than you',
      description:
        '<strong>Run a content gap analysis</strong> against the top competitor domains in the table above.',
      cta: 'See top domains',
      action: () => {
        const el = document.querySelector('.si-table')
        if (el) el.scrollIntoView({ behavior: 'smooth' })
      },
    })
  }
  if (!recs.length) {
    recs.push({
      headline: 'Keep building your citation footprint',
      description:
        'Run more audits to build a richer source-influence picture across providers.',
      cta: 'Run new audit',
      action: () => router.push(`/llm-ranking/${websiteId}`),
    })
  }
  return recs.slice(0, 3)
})

function filterByClass(cls) {
  const matching = recentCitations.value.filter((c) => c.source_class === cls)
  drawerCitations.value = matching
  drawerProvider.value = providerFilter.value || 'All providers'
  drawerPrompt.value = `${titleCase(cls)} citations`
  drawerOpen.value = true
}
</script>

<style scoped>
.si-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.si-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.si-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary, #111);
}
.si-subtitle {
  margin: 4px 0 0;
  color: var(--text-muted, #6b7280);
  font-size: 13px;
}
.si-controls {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.si-segmented {
  display: inline-flex;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-elevated, #fff);
}
.si-seg-btn {
  background: transparent;
  border: 0;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-secondary, #4b5563);
}
.si-seg-btn.active {
  background: var(--accent, #ec4899);
  color: white;
}
.si-loading {
  padding: 40px;
  text-align: center;
  color: var(--text-muted, #6b7280);
}
.si-empty {
  padding: 60px 20px;
  text-align: center;
  border: 1px dashed var(--border, #e5e7eb);
  border-radius: 12px;
  background: var(--bg-elevated, #fff);
}
.si-empty-illus { color: var(--text-muted, #9ca3af); margin-bottom: 12px; }
.si-empty-title { font-size: 18px; font-weight: 600; margin: 0 0 6px; }
.si-empty-copy { color: var(--text-muted, #6b7280); margin: 0 0 16px; }
.si-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.si-stat {
  background: var(--bg-elevated, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 10px;
  padding: 14px 16px;
}
.si-stat-label { font-size: 12px; color: var(--text-muted, #6b7280); }
.si-stat-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary, #111);
  margin-top: 4px;
}
.si-stat-unit { font-size: 13px; font-weight: 500; color: var(--text-muted, #6b7280); margin-left: 2px; }
.si-stat-sub { font-size: 11px; color: var(--text-muted, #6b7280); margin-top: 2px; }
.si-section { margin-bottom: 32px; }
.si-section-title { font-size: 16px; font-weight: 600; margin: 0 0 12px; }
.si-card {
  background: var(--bg-elevated, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
}
.si-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 12px;
}
.si-card-title { font-size: 14px; font-weight: 600; }
.si-card-sub { font-size: 12px; color: var(--text-muted, #6b7280); }
.si-card-line { font-size: 12px; color: var(--text-secondary, #4b5563); margin: 8px 0 0; }
.si-domains-mini { margin-top: 12px; }
.si-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.si-table th, .si-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border, #f1f5f9);
}
.si-table th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted, #6b7280); }
.si-table th.num, .si-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.si-table th.sortable { cursor: pointer; user-select: none; }
.si-table tr.clickable { cursor: pointer; }
.si-table tr.clickable:hover { background: var(--bg-hover, #f9fafb); }
.si-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
}
.si-pill-you { background: #d1fae5; color: #065f46; }
.si-pill-comp { background: #fef3c7; color: #92400e; }
.si-pill-other { background: #f1f5f9; color: #475569; }
.si-table-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
}
.si-muted { color: var(--text-muted, #6b7280); font-size: 12px; }
.si-link-btn {
  background: transparent;
  border: 0;
  color: var(--accent, #ec4899);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}
.si-link-btn:hover { text-decoration: underline; }
.si-recs { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.si-rec-card {
  background: var(--bg-elevated, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  gap: 12px;
}
.si-rec-icon { color: var(--accent, #ec4899); flex-shrink: 0; }
.si-rec-headline { font-weight: 600; font-size: 13px; margin-bottom: 4px; }
.si-rec-desc { font-size: 13px; color: var(--text-secondary, #4b5563); margin: 0 0 10px; line-height: 1.5; }
.si-btn-primary {
  display: inline-block;
  background: var(--accent, #ec4899);
  color: white;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  text-decoration: none;
  font-weight: 500;
}
.si-btn-secondary {
  background: transparent;
  color: var(--accent, #ec4899);
  border: 1px solid var(--accent, #ec4899);
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
.si-empty-inline { color: var(--text-muted, #6b7280); font-size: 13px; }
@media (max-width: 800px) {
  .si-stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
