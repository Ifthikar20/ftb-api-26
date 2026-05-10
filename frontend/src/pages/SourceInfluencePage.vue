<template>
  <div class="si-page mx-auto max-w-7xl px-6 py-8">
    <!-- Intro card: explain what this page does so users aren't lost. -->
    <header id="si-header" class="si-intro">
      <div class="si-intro-left">
        <span class="si-intro-eyebrow">Citation intelligence</span>
        <h1 class="si-intro-h">Source Influence</h1>
        <p class="si-intro-sub">
          Every time Claude, GPT-4, Gemini, or Perplexity answers a question in your
          category, it cites a handful of sources. This page rolls up those citations so you can see
          <strong>which websites the AIs trust most</strong>, where your brand shows up,
          and which domains you should be earning links from next.
        </p>
        <p v-if="websiteName" class="si-intro-meta">For <strong>{{ websiteName }}</strong></p>
      </div>
      <div class="si-intro-right">
        <div class="si-howto">
          <div class="si-howto-h">What to do here</div>
          <ol class="si-howto-list">
            <li>Pick a window (7 / 30 / 90 days) and a provider.</li>
            <li>Scan the top-line stats — your share vs competitors.</li>
            <li>Open <em>Top domains</em> to find pitch / partnership targets.</li>
            <li>Act on the recommendations at the bottom.</li>
          </ol>
        </div>
      </div>
    </header>

    <!-- Filter row -->
    <div class="si-filter-row">
      <div id="si-controls" class="flex flex-wrap items-center gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <AirChip
            v-for="opt in periodOptions"
            :key="opt.value"
            as="button"
            size="sm"
            :variant="periodDays === opt.value ? 'primary' : 'neutral'"
            @click="periodDays = opt.value"
          >
            {{ opt.label }}
          </AirChip>
        </div>
        <span class="hidden h-4 w-px sm:block" style="background: var(--border-color)" aria-hidden="true"></span>
        <div class="flex flex-wrap items-center gap-2">
          <AirChip
            v-for="opt in providerOptions"
            :key="opt.value || 'all'"
            as="button"
            size="sm"
            :variant="providerFilter === opt.value ? 'primary' : 'neutral'"
            @click="providerFilter = opt.value"
          >
            {{ opt.label }}
          </AirChip>
        </div>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <div
        v-for="i in 4"
        :key="i"
        class="h-28 animate-pulse rounded-2xl"
        style="background: var(--bg-card); border: 1px solid var(--border-color)"
      ></div>
    </div>

    <template v-else>
      <!-- Empty state -->
      <div
        v-if="totalCitations === 0"
        class="flex flex-col items-center justify-center rounded-3xl border border-dashed px-8 py-16 text-center"
        style="border-color: var(--border-color); background: var(--bg-card)"
      >
        <div class="mb-4" style="color: var(--text-muted)">
          <svg width="64" height="64" viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="40" cy="40" r="30" stroke-dasharray="4 4" />
            <path d="M28 40h24M40 28v24" stroke-linecap="round" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold" style="color: var(--text-primary)">No citations yet</h2>
        <p class="mt-2 max-w-md text-sm" style="color: var(--text-secondary)">
          Run an audit to start tracking which sources LLMs cite for your category.
        </p>
        <AirButton
          as="router-link"
          :to="`/llm-ranking/${websiteId}`"
          variant="primary"
          size="md"
          class="mt-6"
        >
          Run new audit
        </AirButton>
      </div>

      <template v-else>
        <!-- Top stat row -->
        <section
          id="si-stats"
          class="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4"
        >
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Total citations</AirCardSubtitle>
            <div class="mt-1 text-2xl font-semibold tabular-nums" style="color: var(--text-primary)">
              {{ totalCitations.toLocaleString() }}
            </div>
            <div class="mt-1 text-xs" style="color: var(--text-muted)">
              over last {{ periodDays }} days
            </div>
          </AirCard>
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Unique domains</AirCardSubtitle>
            <div class="mt-1 text-2xl font-semibold tabular-nums" style="color: var(--text-primary)">
              {{ uniqueDomains.toLocaleString() }}
            </div>
            <div class="mt-1 text-xs" style="color: var(--text-muted)">distinct apex domains</div>
          </AirCard>
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Your-site share</AirCardSubtitle>
            <div class="mt-1 flex items-baseline gap-1">
              <span class="text-2xl font-semibold tabular-nums" style="color: var(--text-primary)">
                {{ pct(yourSiteShare) }}
              </span>
              <span class="text-sm" style="color: var(--text-muted)">%</span>
            </div>
            <div class="mt-1 text-xs" style="color: var(--text-muted)">
              {{ yourSiteCount }} citations
            </div>
          </AirCard>
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Competitor share</AirCardSubtitle>
            <div class="mt-1 flex items-baseline gap-1">
              <span class="text-2xl font-semibold tabular-nums" style="color: var(--text-primary)">
                {{ pct(competitorShare) }}
              </span>
              <span class="text-sm" style="color: var(--text-muted)">%</span>
            </div>
            <div class="mt-1 text-xs" style="color: var(--text-muted)">
              {{ competitorCount }} citations
            </div>
          </AirCard>
        </section>

        <!-- Per-provider breakdown cards -->
        <section id="si-providers" class="mb-10">
          <h2 class="mb-4 text-lg font-semibold" style="color: var(--text-primary)">
            Source mix by provider
          </h2>
          <div
            v-if="!providerCards.length"
            class="rounded-2xl border border-dashed px-6 py-10 text-center text-sm"
            style="border-color: var(--border-color); color: var(--text-muted)"
          >
            No per-provider rollups for this window yet.
          </div>
          <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <AirCard v-for="card in providerCards" :key="card.provider" size="md" interactive>
              <div class="mb-3 flex items-start justify-between gap-3">
                <div>
                  <div class="text-[15px] font-semibold" style="color: var(--text-primary)">
                    {{ providerLabel(card.provider) }}
                  </div>
                  <div class="text-xs" style="color: var(--text-muted)">
                    {{ card.total.toLocaleString() }} citations
                  </div>
                </div>
                <AirButton
                  variant="link"
                  size="sm"
                  @click.stop="card.expanded = !card.expanded"
                >
                  {{ card.expanded ? 'Hide top domains' : 'View top domains' }}
                </AirButton>
              </div>
              <SourceBreakdownBar :breakdown="card.breakdown" :height="14" />
              <p v-if="card.topClass" class="mt-3 text-xs" style="color: var(--text-secondary)">
                Top source:
                <strong style="color: var(--text-primary)">{{ titleCase(card.topClass.source_class) }}</strong>
                ({{ pct(card.topClass.share) }}%)
              </p>
              <div
                v-if="card.expanded"
                class="mt-4 rounded-xl"
                style="background: var(--bg-surface); border: 1px solid var(--border-color)"
              >
                <table class="w-full text-left text-sm">
                  <thead>
                    <tr>
                      <th class="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">
                        Domain
                      </th>
                      <th class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">
                        Count
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="d in card.top_domains.slice(0, 10)"
                      :key="d.apex_domain"
                      style="border-top: 1px solid var(--border-color)"
                    >
                      <td class="px-3 py-2" style="color: var(--text-primary)">{{ d.apex_domain }}</td>
                      <td class="px-3 py-2 text-right tabular-nums" style="color: var(--text-secondary)">
                        {{ d.count }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </AirCard>
          </div>
        </section>

        <!-- Top domains card -->
        <section class="mb-10">
          <h2 class="mb-4 text-lg font-semibold" style="color: var(--text-primary)">Top domains</h2>
          <AirCard size="md" :padded="false">
            <table class="w-full text-left text-sm">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color)">
                  <th class="cursor-pointer px-4 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)" @click="toggleSort('apex_domain')">
                    Domain
                    <span v-if="sortKey === 'apex_domain'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="cursor-pointer px-4 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)" @click="toggleSort('source_class')">
                    Source class
                    <span v-if="sortKey === 'source_class'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="cursor-pointer px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)" @click="toggleSort('count')">
                    Count
                    <span v-if="sortKey === 'count'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="cursor-pointer px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)" @click="toggleSort('share')">
                    Share
                    <span v-if="sortKey === 'share'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                  <th class="cursor-pointer px-4 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)" @click="toggleSort('type')">
                    Type
                    <span v-if="sortKey === 'type'">{{ sortDir === 'desc' ? '↓' : '↑' }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in visibleDomains"
                  :key="row.apex_domain"
                  class="cursor-pointer transition-colors"
                  style="border-top: 1px solid var(--border-color)"
                  @click="openDomainDrawer(row)"
                  @mouseover="(e) => e.currentTarget.style.background='var(--bg-card-hover)'"
                  @mouseleave="(e) => e.currentTarget.style.background=''"
                >
                  <td class="px-4 py-3" style="color: var(--text-primary)">{{ row.apex_domain }}</td>
                  <td class="px-4 py-3">
                    <SourceClassBadge :source_class="row.source_class || 'other'" />
                  </td>
                  <td class="px-4 py-3 text-right tabular-nums" style="color: var(--text-secondary)">
                    {{ row.count }}
                  </td>
                  <td class="px-4 py-3 text-right tabular-nums" style="color: var(--text-secondary)">
                    {{ pct(row.share) }}%
                  </td>
                  <td class="px-4 py-3">
                    <AirChip v-if="row.is_target" variant="success" size="xs">Your site</AirChip>
                    <AirChip v-else-if="row.is_competitor" variant="warning" size="xs">Competitor</AirChip>
                    <AirChip v-else variant="neutral" size="xs">Other</AirChip>
                  </td>
                </tr>
              </tbody>
            </table>
            <div
              class="flex items-center justify-between px-4 py-3"
              style="border-top: 1px solid var(--border-color)"
            >
              <span class="text-xs" style="color: var(--text-muted)">
                Showing {{ Math.min(visibleDomains.length, sortedDomains.length) }}
                of {{ sortedDomains.length }}
              </span>
              <AirButton
                v-if="domainLimit < sortedDomains.length"
                variant="link"
                size="sm"
                @click="domainLimit += 30"
              >
                Show more
              </AirButton>
            </div>
          </AirCard>
        </section>

        <!-- Recommendations -->
        <section id="si-recs" class="mb-10">
          <h2 class="mb-4 text-lg font-semibold" style="color: var(--text-primary)">
            Recommendations
          </h2>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            <AirCard v-for="(rec, i) in recommendations" :key="i" size="md" interactive>
              <div class="flex items-start gap-3">
                <div
                  class="si-rec-icon flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                >
                  <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                    <circle cx="10" cy="10" r="8" />
                    <path d="M10 6v5M10 13.5h.01" stroke-linecap="round" />
                  </svg>
                </div>
                <div class="min-w-0 flex-1">
                  <div class="text-sm font-semibold" style="color: var(--text-primary)">
                    {{ rec.headline }}
                  </div>
                  <p class="mt-1 text-[13px] leading-relaxed" style="color: var(--text-secondary)" v-html="rec.description"></p>
                  <AirButton
                    v-if="rec.cta"
                    variant="outline"
                    size="sm"
                    class="mt-3"
                    @click="rec.action && rec.action()"
                  >
                    {{ rec.cta }}
                  </AirButton>
                </div>
              </div>
            </AirCard>
          </div>
        </section>
      </template>
    </template>

    <CitationsDrawer
      v-model:open="drawerOpen"
      :citations="drawerCitations"
      :provider="drawerProvider"
      :prompt="drawerPrompt"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import citationsApi from '@/api/citations'
import SourceClassBadge from '@/components/citations/SourceClassBadge.vue'
import SourceBreakdownBar from '@/components/citations/SourceBreakdownBar.vue'
import AirButton from '@/components/ui/AirButton.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirCardSubtitle from '@/components/ui/AirCardSubtitle.vue'
import AirChip from '@/components/ui/AirChip.vue'
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

const yourSiteCount = computed(() => aggregateBreakdown.value.breakdown.your_site?.count || 0)
const yourSiteShare = computed(() => aggregateBreakdown.value.breakdown.your_site?.share || 0)
const competitorCount = computed(() => aggregateBreakdown.value.breakdown.competitor_site?.count || 0)
const competitorShare = computed(() => aggregateBreakdown.value.breakdown.competitor_site?.share || 0)

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
.si-page { background: #f7f9fc; min-height: 100vh; }

/* Intro: side-by-side explainer card */
.si-intro {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
  gap: 22px;
  padding: 28px;
  margin-bottom: 22px;
  background: linear-gradient(135deg, #ffffff 0%, #f1f5fb 100%);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 12px 30px rgba(15, 23, 42, 0.05);
}
.si-intro-eyebrow {
  display: inline-block;
  font-size: 11px; font-weight: 700; letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #ff6b35;
  padding: 4px 10px;
  border-radius: 9999px;
  background: rgba(255, 107, 53, 0.10);
  margin-bottom: 14px;
}
.si-intro-h {
  font-size: 28px; font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
  margin: 0 0 10px;
}
.si-intro-sub {
  font-size: 14.5px; line-height: 1.55;
  color: #475569;
  margin: 0;
  max-width: 640px;
}
.si-intro-sub strong { color: #0f172a; font-weight: 600; }
.si-intro-meta {
  margin-top: 14px;
  font-size: 12.5px;
  color: #64748b;
}
.si-intro-meta strong { color: #1f2937; font-weight: 600; }

.si-howto {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  padding: 18px 20px;
}
.si-howto-h {
  font-size: 12px; font-weight: 700;
  color: #ff6b35; letter-spacing: 0.06em; text-transform: uppercase;
  margin-bottom: 10px;
}
.si-howto-list {
  margin: 0; padding-left: 18px;
  font-size: 13px; line-height: 1.6;
  color: #334155;
}
.si-howto-list li { margin-bottom: 4px; }
.si-howto-list em { color: #3b82f6; font-style: normal; font-weight: 600; }

/* Filter row sits on its own */
.si-filter-row {
  display: flex; justify-content: flex-end;
  margin-bottom: 22px;
}

/* Recommendation icon — light-themed, brand-orange */
.si-rec-icon {
  background: rgba(255, 107, 53, 0.12);
  color: #ff6b35;
}

@media (max-width: 880px) {
  .si-intro { grid-template-columns: 1fr; padding: 22px; }
  .si-filter-row { justify-content: flex-start; }
}
</style>
