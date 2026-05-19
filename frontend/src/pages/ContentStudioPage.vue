<template>
  <div class="cs-page mx-auto max-w-7xl px-6 py-12 sm:px-8 lg:px-12">
    <!-- Header -->
    <header id="cs-header" class="mb-12 max-w-3xl">
      <div class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-500">
        Content Studio
      </div>
      <h1 class="text-4xl font-semibold leading-tight tracking-tight text-zinc-900 sm:text-[40px]">
        Write the things AI assistants miss.
      </h1>
      <p class="mt-3 text-base leading-relaxed text-zinc-500">
        AI-drafted blogs, FAQs, JSON-LD and Reddit replies to close your visibility,
        accuracy, and citation gaps. We surface every place AI could mention you better
        and let you ship a fix in a few clicks.
      </p>
    </header>

    <!-- Stats strip -->
    <section id="cs-stats" class="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <AirCard size="md">
        <AirCardHeader>
          <AirCardSubtitle class="text-xs font-semibold uppercase tracking-wider">
            Open briefs
          </AirCardSubtitle>
        </AirCardHeader>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-semibold tabular-nums text-zinc-900">{{ stats.open }}</span>
          <span class="text-sm text-zinc-500">waiting for you</span>
        </div>
      </AirCard>
      <AirCard size="md">
        <AirCardHeader>
          <AirCardSubtitle class="text-xs font-semibold uppercase tracking-wider">
            Drafts in progress
          </AirCardSubtitle>
        </AirCardHeader>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-semibold tabular-nums text-zinc-900">{{ stats.drafting }}</span>
          <span class="text-sm text-zinc-500">being written</span>
        </div>
      </AirCard>
      <AirCard size="md">
        <AirCardHeader>
          <AirCardSubtitle class="text-xs font-semibold uppercase tracking-wider">
            Approved as publish content
          </AirCardSubtitle>
        </AirCardHeader>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-semibold tabular-nums text-zinc-900">{{ stats.published }}</span>
        </div>
      </AirCard>
    </section>

    <!-- Filter bar -->
    <section id="cs-filters" class="mb-8 flex flex-wrap items-center gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <AirChip
          v-for="g in gapFilters"
          :key="g.value"
          as="button"
          size="sm"
          :variant="filters.gap === g.value ? 'primary' : 'neutral'"
          @click="filters.gap = g.value"
        >
          {{ g.label }}
        </AirChip>
      </div>
      <span class="hidden h-4 w-px bg-zinc-200 sm:block" aria-hidden="true"></span>
      <div class="flex flex-wrap items-center gap-2">
        <AirChip
          v-for="f in formatFilters"
          :key="f.value"
          as="button"
          size="xs"
          :variant="filters.format === f.value ? 'primary' : 'neutral'"
          @click="filters.format = f.value"
        >
          {{ f.label }}
        </AirChip>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <span class="text-xs text-zinc-500">Sort</span>
        <select
          v-model="filters.sort"
          class="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 outline-none focus:border-rose-300"
        >
          <option value="impact">Highest impact</option>
          <option value="newest">Newest</option>
        </select>
      </div>
    </section>

    <!-- Loading -->
    <div v-if="loading" class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="i in 6"
        :key="i"
        class="h-56 animate-pulse rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
      ></div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!filteredBriefs.length"
      class="flex flex-col items-center justify-center rounded-3xl border border-dashed border-zinc-200 bg-white px-8 py-20 text-center"
    >
      <div class="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-500">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 4h11l3 3v13H5z" />
          <path d="M16 4v3h3" />
          <path d="M8 12h8M8 16h6" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-zinc-900">No briefs in this view yet.</h3>
      <p class="mt-2 max-w-md text-sm text-zinc-500">
        Run an audit to start building your content queue. Once we know where AI assistants
        miss you, we'll suggest exactly what to write.
      </p>
      <AirButton variant="primary" size="lg" class="mt-6" @click="goToLLMRanking">
        Open LLM Dashboard
      </AirButton>
    </div>

    <!-- Brief grid -->
    <div
      v-else
      id="cs-grid"
      class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3"
    >
      <BriefCard
        v-for="brief in filteredBriefs"
        :key="brief.id"
        :brief="brief"
        @select="onSelect"
        @skip="onSkip"
      />
    </div>

    <!-- Onboarding tour -->
    <OnboardingTooltip :steps="tourSteps" :storage-key="'fb_tour_content_studio_v1'" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import contentStudioApi from '@/api/contentStudio'
import BriefCard from '@/components/content_studio/BriefCard.vue'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const websiteId = computed(() => route.params.websiteId)

const loading = ref(false)
const briefs = ref([])
const drafting = ref(new Set())

const stats = ref({ open: 0, drafting: 0, published: 0 })

const filters = reactive({
  gap: 'all',
  format: 'all',
  sort: 'impact',
})

const gapFilters = [
  { value: 'all', label: 'All' },
  { value: 'visibility', label: 'Visibility' },
  { value: 'accuracy', label: 'Accuracy' },
  { value: 'citation', label: 'Citation' },
]

const formatFilters = [
  { value: 'all', label: 'All formats' },
  { value: 'blog', label: 'Blog' },
  { value: 'faq', label: 'FAQ' },
  { value: 'reddit', label: 'Reddit' },
  { value: 'json_ld', label: 'JSON-LD' },
  { value: 'landing', label: 'Landing' },
]

const tourSteps = [
  { target: '#cs-header', title: 'Welcome to Content Studio', message: 'AI drafts content to fix the gaps your audits surface — visibility, accuracy, and citations.', position: 'bottom' },
  { target: '#cs-stats', title: 'Your gaps, ranked by impact', message: 'These are the briefs waiting on you, drafts in flight, and what shipped this month.', position: 'bottom' },
  { target: '#cs-filters', title: 'Focus on what matters', message: 'Filter to focus on visibility, accuracy, or citation gaps — and on the format you care about.', position: 'bottom' },
  { target: '#cs-grid', title: 'One click to start', message: 'Click "Create draft" on any card and we\'ll write the first version using your Brand Vault facts.', position: 'top' },
]

const filteredBriefs = computed(() => {
  let list = briefs.value
  if (filters.gap !== 'all') list = list.filter((b) => b.gap_type === filters.gap)
  if (filters.format !== 'all') list = list.filter((b) => b.target_format === filters.format)
  if (filters.sort === 'newest') {
    list = [...list].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
  } else {
    list = [...list].sort((a, b) => (Number(b.impact_score) || 0) - (Number(a.impact_score) || 0))
  }
  return list
})

function goToLLMRanking() {
  router.push(`/llm-ranking/${websiteId.value}`)
}

async function loadBriefs() {
  if (!websiteId.value) return
  loading.value = true
  try {
    const params = { status: 'pending' }
    const { data } = await contentStudioApi.briefs(websiteId.value, params)
    const body = data?.data || data || {}
    const list = body.results || body || []
    briefs.value = Array.isArray(list) ? list : []
    computeStats()
  } catch {
    briefs.value = []
  } finally {
    loading.value = false
  }
}

function computeStats() {
  let open = 0
  let drafted = 0
  let approved = 0
  for (const b of briefs.value) {
    if (b.status === 'pending') open += 1
    if (b.status === 'drafting' || b.status === 'drafted') drafted += 1
    if (b.status === 'approved') approved += 1
  }
  stats.value.open = open
  stats.value.drafting = drafted
  stats.value.published = approved
}

async function onSelect(brief) {
  if (drafting.value.has(brief.id)) return
  drafting.value.add(brief.id)
  try {
    const { data } = await contentStudioApi.draftBrief(brief.id)
    const body = data?.data || data || {}
    const draftId = body.id || body.draft_id
    if (draftId) {
      router.push(`/llm-ranking/${websiteId.value}/content/drafts/${draftId}`)
      return
    }
    toast.success('We\'re writing your draft. It will appear in a moment.')
    setTimeout(loadBriefs, 1500)
  } catch {
    // toast handled by api client
  } finally {
    drafting.value.delete(brief.id)
  }
}

async function onSkip(brief) {
  try {
    await contentStudioApi.skipBrief(brief.id)
    briefs.value = briefs.value.filter((b) => b.id !== brief.id)
    computeStats()
    toast.success('Brief skipped.')
  } catch {
    // handled
  }
}

onMounted(() => {
  loadBriefs()
})
</script>
