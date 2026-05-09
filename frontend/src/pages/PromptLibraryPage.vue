<template>
  <div class="mx-auto max-w-7xl px-6 py-8">
    <!-- Header -->
    <header id="pl-header" class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight" style="color: var(--text-primary)">
          Prompts marketplace
        </h1>
        <p class="mt-1 max-w-2xl text-sm" style="color: var(--text-secondary)">
          Real questions people ask AI assistants. Pick an industry to browse, see the
          live Google Trends pulse for that category, and add the prompts that fit your
          brand to your audit set.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <select
          id="pl-industry"
          v-model="industrySlug"
          class="pl-control min-w-[16rem]"
        >
          <option value="">Select an industry…</option>
          <option v-for="ind in industries" :key="ind.id" :value="ind.slug">
            {{ ind.name }}
          </option>
        </select>
      </div>
    </header>

    <!-- Filter row -->
    <section id="pl-filters" class="mb-5 flex flex-wrap items-center gap-2">
      <AirChip
        v-for="bucket in buckets"
        :key="bucket.value"
        as="button"
        size="sm"
        :variant="bucket.value === intent ? 'primary' : 'neutral'"
        @click="intent = bucket.value"
      >
        {{ bucket.label }}
      </AirChip>
      <span class="hidden h-4 w-px sm:block" style="background: var(--border-color)" aria-hidden="true"></span>
      <input
        v-model="searchInput"
        type="search"
        placeholder="Search prompts…"
        class="pl-control w-64"
      />
      <select v-model="sort" class="pl-control">
        <option value="demand">Most asked</option>
        <option value="newest">Newest</option>
        <option value="alpha">A–Z</option>
      </select>
      <span class="ml-auto text-xs" style="color: var(--text-muted)">
        {{ filteredPrompts.length }} prompts
        <template v-if="websiteId">· {{ brandPromptIds.size }} in your set</template>
      </span>
    </section>

    <!-- Industry trend (real) -->
    <AirCard v-if="industrySlug" size="md" class="mb-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <AirCardSubtitle class="text-xs uppercase tracking-wide">Google Trends · {{ activeIndustryName }}</AirCardSubtitle>
          <div class="mt-1 text-base font-semibold" style="color: var(--text-primary)">
            <template v-if="trends?.keyword">"{{ trends.keyword }}"</template>
            <template v-else>—</template>
          </div>
          <p class="mt-1 text-xs" style="color: var(--text-secondary)">
            <template v-if="trends?.refreshed_at">
              12-month interest, refreshed {{ formatRelative(trends.refreshed_at) }}
            </template>
            <template v-else-if="trendsLoading">Fetching live trends…</template>
            <template v-else-if="trends?.error">
              Live trends unavailable right now
              <span class="ml-1 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider" style="background: var(--color-warning-bg, rgba(245,158,11,0.12)); color: var(--color-warning, rgb(180,83,9))">
                {{ trendsErrorLabel(trends.error) }}
              </span>
            </template>
            <template v-else>No trend data yet</template>
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <AirChip
            v-for="(g, i) in trends?.top_regions || []"
            :key="g.code + i"
            :variant="i === 0 ? 'primary' : 'neutral'"
            size="sm"
          >
            {{ g.name }} · {{ g.value }}
          </AirChip>
          <span v-if="!(trends?.top_regions?.length)" class="text-xs" style="color: var(--text-muted)">
            No region data
          </span>
        </div>
      </div>
      <div class="mt-4">
        <Sparkline :values="(trends?.interest_over_time || []).map(p => p.value)" />
      </div>
    </AirCard>

    <!-- Loading -->
    <div v-if="loading" class="rounded-2xl" style="border: 1px solid var(--border-color); background: var(--bg-card)">
      <div v-for="i in 6" :key="i" class="h-14 animate-pulse" :style="i < 6 ? 'border-bottom: 1px solid var(--border-color)' : ''"></div>
    </div>

    <!-- Empty: no industry selected -->
    <div
      v-else-if="!industrySlug"
      class="flex flex-col items-center justify-center rounded-3xl border border-dashed px-8 py-16 text-center"
      style="border-color: var(--border-color); background: var(--bg-card)"
    >
      <div class="mb-3" style="color: var(--text-muted)">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="6" y="6" width="36" height="36" rx="8" />
          <path d="M14 24h20M24 14v20" stroke-linecap="round" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold" style="color: var(--text-primary)">Pick an industry to start browsing</h3>
      <p class="mt-2 max-w-md text-sm" style="color: var(--text-secondary)">
        We have prompts mined for {{ industries.length || '20+' }} industries. Select one above
        to see what real users are asking AI assistants in that category.
      </p>
    </div>

    <!-- Empty: filters -->
    <div
      v-else-if="!filteredPrompts.length"
      class="rounded-3xl border border-dashed p-10 text-center text-sm"
      style="border-color: var(--border-color); background: var(--bg-card); color: var(--text-muted)"
    >
      No prompts match these filters.
    </div>

    <!-- Raw prompt table -->
    <AirCard v-else size="md" :padded="false">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-color)">
              <th class="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Prompt</th>
              <th class="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Intent</th>
              <th class="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Source</th>
              <th class="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Demand</th>
              <th class="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Added</th>
              <th class="px-3 py-3 text-right text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in filteredPrompts"
              :key="p.id"
              class="pl-row"
              style="border-top: 1px solid var(--border-color)"
            >
              <td class="px-4 py-3 align-top" style="color: var(--text-primary); max-width: 40rem">
                <div class="leading-snug font-medium">{{ p.text }}</div>
                <p
                  v-if="p.excerpt"
                  class="mt-1 line-clamp-3 whitespace-pre-line text-xs leading-relaxed"
                  style="color: var(--text-secondary)"
                >
                  {{ p.excerpt }}
                </p>
                <div v-if="p.source_url" class="mt-1.5">
                  <a
                    :href="p.source_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1 text-xs hover:underline"
                    style="color: var(--brand-accent)"
                    @click.stop
                  >
                    {{ p.source_label || p.source }} ↗
                  </a>
                </div>
              </td>
              <td class="px-3 py-3 align-top">
                <AirChip :variant="intentVariant(p.intent_bucket)" size="xs">
                  {{ intentLabel(p.intent_bucket) }}
                </AirChip>
              </td>
              <td class="px-3 py-3 align-top">
                <AirChip variant="neutral" size="xs">{{ p.source_label || p.source }}</AirChip>
              </td>
              <td class="px-3 py-3 align-top">
                <DemandBar :score="p.demand_score" />
              </td>
              <td class="px-3 py-3 align-top text-xs" style="color: var(--text-muted)">
                {{ formatDate(p.created_at) }}
              </td>
              <td class="px-3 py-3 align-top text-right">
                <template v-if="!websiteId">
                  <AirButton
                    variant="outline"
                    size="sm"
                    as="router-link"
                    to="/websites"
                  >
                    Pick a website
                  </AirButton>
                </template>
                <template v-else-if="brandPromptIds.has(p.id)">
                  <AirButton
                    variant="ghost"
                    size="sm"
                    @click="onRemove(p)"
                    :disabled="busyId === p.id"
                  >
                    Added ✓
                  </AirButton>
                </template>
                <template v-else>
                  <AirButton
                    variant="primary"
                    size="sm"
                    @click="onAdd(p)"
                    :loading="busyId === p.id"
                    :disabled="busyId === p.id"
                  >
                    Add
                  </AirButton>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </AirCard>

    <OnboardingTooltip storage-key="fb_tour_prompt_library_v3" :steps="tourSteps" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, h } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import promptLibrary from '@/api/promptLibrary'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirCardSubtitle from '@/components/ui/AirCardSubtitle.vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'

const route = useRoute()
const toast = useToast()

const websiteId = computed(() => route.params.websiteId || null)

const industries = ref([])
const industrySlug = ref('')
const intent = ref('')
const sort = ref('demand')
const searchInput = ref('')
const debouncedSearch = ref('')
let searchTimer = null
watch(searchInput, (v) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { debouncedSearch.value = v }, 250)
})

const prompts = ref([])
const loading = ref(false)

const trends = ref(null)
const trendsLoading = ref(false)

const brandPromptList = ref([])
const brandPromptIds = computed(() => new Set(brandPromptList.value.map((b) => b.prompt?.id)))
const busyId = ref(null)

const buckets = [
  { value: '', label: 'All intents' },
  { value: 'category', label: 'Category' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'problem', label: 'Problem' },
  { value: 'local', label: 'Local' },
]

const tourSteps = [
  {
    target: '#pl-header',
    title: 'Marketplace of real questions',
    message: 'Pick an industry to see real prompts from our library, alongside live Google Trends data for that category.',
    position: 'bottom',
  },
  {
    target: '#pl-industry',
    title: 'Pick your industry',
    message: 'Each industry has its own demand pattern. Select Food & Beverages, SaaS, Nonprofit — whatever applies.',
    position: 'left',
  },
  {
    target: '#pl-filters',
    title: 'Filter and sort',
    message: 'Narrow by intent (Category / Comparison / Problem / Local) or sort by demand.',
    position: 'bottom',
  },
]

const activeIndustryName = computed(
  () => industries.value.find((i) => i.slug === industrySlug.value)?.name || '',
)

const filteredPrompts = computed(() => {
  let list = prompts.value
  if (sort.value === 'newest') {
    list = [...list].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
  } else if (sort.value === 'alpha') {
    list = [...list].sort((a, b) => (a.text || '').localeCompare(b.text || ''))
  } else {
    list = [...list].sort((a, b) => (b.demand_score || 0) - (a.demand_score || 0))
  }
  return list
})

async function loadIndustries() {
  try {
    const { data } = await promptLibrary.getIndustries()
    industries.value = data?.results || data?.data || data || []
  } catch {
    industries.value = []
  }
}

async function loadPrompts() {
  if (!industrySlug.value) {
    prompts.value = []
    return
  }
  loading.value = true
  try {
    const params = { limit: 200, industry: industrySlug.value }
    if (intent.value) params.intent_bucket = intent.value
    if (debouncedSearch.value) params.search = debouncedSearch.value
    const { data } = await promptLibrary.getPrompts(params)
    const rows = data?.data?.results || data?.results || data?.data || data || []
    prompts.value = Array.isArray(rows) ? rows : []
  } catch {
    prompts.value = []
  } finally {
    loading.value = false
  }
}

async function loadTrends() {
  if (!industrySlug.value) {
    trends.value = null
    return
  }
  trendsLoading.value = true
  try {
    const { data } = await promptLibrary.getIndustryTrends(industrySlug.value)
    trends.value = data?.data || data || null
  } catch {
    trends.value = null
  } finally {
    trendsLoading.value = false
  }
}

async function loadBrandPrompts() {
  if (!websiteId.value) {
    brandPromptList.value = []
    return
  }
  try {
    const { data } = await promptLibrary.listBrandPrompts(websiteId.value)
    brandPromptList.value = data?.data || data || []
  } catch {
    brandPromptList.value = []
  }
}

async function onAdd(prompt) {
  if (!websiteId.value || busyId.value) return
  busyId.value = prompt.id
  try {
    const { data } = await promptLibrary.addBrandPrompt(websiteId.value, prompt.id)
    const bp = data?.data || data
    if (bp) brandPromptList.value = [bp, ...brandPromptList.value]
    toast.success('Added to your prompts.')
  } catch (e) {
    toast.error(e.displayMessage || 'Could not add prompt.')
  } finally {
    busyId.value = null
  }
}

async function onRemove(prompt) {
  if (!websiteId.value || busyId.value) return
  const bp = brandPromptList.value.find((b) => b.prompt?.id === prompt.id)
  if (!bp) return
  busyId.value = prompt.id
  try {
    await promptLibrary.removeBrandPrompt(bp.id)
    brandPromptList.value = brandPromptList.value.filter((b) => b.id !== bp.id)
    toast.success('Removed from your prompts.')
  } catch (e) {
    toast.error(e.displayMessage || 'Could not remove prompt.')
  } finally {
    busyId.value = null
  }
}

function intentLabel(b) {
  const m = { category: 'Category', comparison: 'Comparison', problem: 'Problem', local: 'Local' }
  return m[b] || b
}
function intentVariant(b) {
  const m = { category: 'info', comparison: 'primary', problem: 'warning', local: 'success' }
  return m[b] || 'neutral'
}

function formatDate(v) {
  if (!v) return ''
  try { return new Date(v).toLocaleDateString() } catch { return '' }
}

function formatRelative(iso) {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  const diff = Date.now() - then
  const mins = Math.round(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.round(hrs / 24)
  return `${days}d ago`
}

function trendsErrorLabel(err) {
  if (!err) return ''
  if (err.includes('429')) return 'rate limited'
  if (err.toLowerCase().includes('timeout')) return 'timed out'
  return 'unavailable'
}

const Sparkline = {
  props: { values: { type: Array, default: () => [] } },
  setup(props) {
    return () => {
      const v = props.values
      if (!v.length) {
        return h('span', { style: 'color: var(--text-muted); font-size: 11px' }, 'No trend data yet')
      }
      const w = 720
      const ht = 56
      const max = Math.max(...v)
      const min = Math.min(...v)
      const range = Math.max(1, max - min)
      const pts = v
        .map((val, i) => {
          const x = (i / Math.max(1, v.length - 1)) * w
          const y = ht - ((val - min) / range) * (ht - 6) - 3
          return `${x.toFixed(1)},${y.toFixed(1)}`
        })
        .join(' ')
      return h(
        'svg',
        { width: '100%', height: ht, viewBox: `0 0 ${w} ${ht}`, preserveAspectRatio: 'none', style: 'display:block' },
        [
          h('polyline', {
            points: pts,
            fill: 'none',
            stroke: 'var(--brand-accent)',
            'stroke-width': 1.6,
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round',
          }),
        ],
      )
    }
  },
}

const DemandBar = {
  props: { score: { type: Number, default: 0 } },
  setup(props) {
    return () => {
      const pct = Math.max(0, Math.min(100, Math.round((props.score || 0) * 100)))
      return h('div', { class: 'flex items-center gap-2' }, [
        h(
          'div',
          {
            style:
              'width: 60px; height: 6px; border-radius: 9999px; background: var(--border-color); overflow: hidden',
          },
          [
            h('div', {
              style: `width:${pct}%; height:100%; background: var(--brand-accent); border-radius: 9999px`,
            }),
          ],
        ),
        h(
          'span',
          { style: 'font-size: 11px; color: var(--text-muted); font-variant-numeric: tabular-nums' },
          String(pct),
        ),
      ])
    }
  },
}

onMounted(async () => {
  await loadIndustries()
  await loadBrandPrompts()
})

watch([industrySlug, intent, debouncedSearch], loadPrompts)
watch(industrySlug, loadTrends)
watch(websiteId, loadBrandPrompts)
</script>

<style scoped>
.pl-control {
  border-radius: 9999px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  outline: none;
  transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}
.pl-control:hover {
  border-color: var(--border-hover);
}
.pl-control:focus-visible {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px var(--brand-accent-glow);
}
.pl-row {
  transition: background 120ms ease-out;
}
.pl-row:hover {
  background: var(--bg-card-hover);
}
</style>
