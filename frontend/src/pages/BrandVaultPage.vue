<template>
  <div class="p-6">
    <!-- Header -->
    <header id="bv-header" class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">Brand Vault</h1>
        <p v-if="websiteName" class="text-sm text-gray-500">{{ websiteName }}</p>
      </div>
      <div class="flex items-center gap-2">
        <AirButton variant="outline" size="md" @click="importOpen = true">
          Import facts
        </AirButton>
        <AirButton
          variant="primary"
          size="md"
          :loading="extracting"
          :disabled="extracting"
          @click="onReExtract"
        >
          {{ extracting ? 'Queuing...' : 'Re-extract from sources' }}
        </AirButton>
      </div>
    </header>

    <!-- Stats row -->
    <section id="bv-stats" class="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <AirCard size="md">
        <AirCardSubtitle class="text-xs uppercase tracking-wide">Pending review</AirCardSubtitle>
        <div class="mt-1 text-2xl font-semibold" style="color: var(--color-warning)">{{ stats.pending }}</div>
      </AirCard>
      <AirCard size="md">
        <AirCardSubtitle class="text-xs uppercase tracking-wide">Approved</AirCardSubtitle>
        <div class="mt-1 text-2xl font-semibold" style="color: var(--color-success)">{{ stats.approved }}</div>
      </AirCard>
      <AirCard size="md">
        <AirCardSubtitle class="text-xs uppercase tracking-wide">Rejected</AirCardSubtitle>
        <div class="mt-1 text-2xl font-semibold" style="color: var(--text-secondary)">{{ stats.rejected }}</div>
      </AirCard>
      <AirCard size="md">
        <AirCardSubtitle class="text-xs uppercase tracking-wide">Auto-approved</AirCardSubtitle>
        <div class="mt-1 text-2xl font-semibold" style="color: var(--color-info)">{{ stats.auto }}</div>
      </AirCard>
    </section>

    <!-- Filter bar -->
    <section id="bv-filters" class="mb-6 flex flex-wrap items-center gap-2">
      <select v-model="filters.status" class="bv-filter">
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="auto">Auto-approved</option>
      </select>
      <select v-model="filters.product_line" class="bv-filter">
        <option value="">All product lines</option>
        <option v-for="pl in productLines" :key="pl" :value="pl">{{ pl }}</option>
      </select>
      <select v-model="filters.topic" class="bv-filter">
        <option value="">All topics</option>
        <option v-for="t in topics" :key="t" :value="t">{{ t }}</option>
      </select>
      <input
        v-model="searchInput"
        type="search"
        placeholder="Search facts..."
        class="bv-filter ml-auto w-64"
      />
    </section>

    <!-- Facts grid -->
    <section>
      <div v-if="loading" class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="i in 6"
          :key="i"
          class="h-44 animate-pulse rounded-2xl"
          style="background: var(--bg-card); border: 1px solid var(--border-color)"
        ></div>
      </div>
      <div
        v-else-if="!facts.length"
        class="flex flex-col items-center justify-center rounded-3xl border border-dashed px-8 py-16 text-center"
        style="border-color: var(--border-color); background: var(--bg-card)"
      >
        <p class="text-sm" style="color: var(--text-secondary)">
          No facts yet. Click <strong style="color: var(--text-primary)">Re-extract</strong> to mine your knowledge base.
        </p>
      </div>
      <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <FactRow
          v-for="fact in facts"
          :key="fact.id"
          :fact="fact"
          @approve="onApprove"
          @reject="onReject"
          @edit-click="onEditClick"
        />
      </div>
      <div v-if="facts.length && hasMore" class="mt-6 flex justify-center">
        <AirButton variant="secondary" size="md" :loading="loadingMore" :disabled="loadingMore" @click="loadMore">
          {{ loadingMore ? 'Loading...' : 'Load more' }}
        </AirButton>
      </div>
    </section>

    <EditFactModal
      v-model:open="editOpen"
      :fact="editFact"
      @saved="onEditSaved"
    />

    <ImportFactsModal
      v-model:open="importOpen"
      :website-id="websiteId"
      @imported="onImported"
    />

    <OnboardingTooltip storage-key="fb_tour_brand_vault_v1" :steps="tourSteps" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import brandVaultApi from '@/api/brandVault'
import FactRow from '@/components/brand_vault/FactRow.vue'
import EditFactModal from '@/components/brand_vault/EditFactModal.vue'
import ImportFactsModal from '@/components/brand_vault/ImportFactsModal.vue'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'
import AirButton from '@/components/ui/AirButton.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirCardSubtitle from '@/components/ui/AirCardSubtitle.vue'

const route = useRoute()
const appStore = useAppStore()
const toast = useToast()
const websiteId = route.params.websiteId

const websiteName = computed(() => appStore.activeWebsite?.name || '')

const loading = ref(true)
const loadingMore = ref(false)
const extracting = ref(false)
const facts = ref([])
const nextUrl = ref(null)

const stats = reactive({ pending: 0, approved: 0, rejected: 0, auto: 0 })
const productLines = ref([])
const topics = ref([])

const filters = reactive({ status: '', product_line: '', topic: '' })
const searchInput = ref('')
const debouncedSearch = ref('')

let searchTimer = null
watch(searchInput, (v) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { debouncedSearch.value = v }, 300)
})

const editOpen = ref(false)
const editFact = ref(null)
const importOpen = ref(false)

function onImported() {
  loadFacts()
  loadStats()
}

const tourSteps = [
  {
    target: '#bv-header',
    title: 'Brand Vault',
    message: 'This is your verified source of truth. Every fact AI assistants should know about your brand lives here.',
    position: 'bottom',
  },
  {
    target: '#bv-stats',
    title: 'Review pending facts',
    message: 'Review pending facts to keep the vault accurate. Approved facts become your ground truth for accuracy checks.',
    position: 'bottom',
  },
  {
    target: '#bv-filters',
    title: 'Filter the vault',
    message: 'Filter by product line, topic, or status to focus your review.',
    position: 'bottom',
  },
]

const hasMore = computed(() => !!nextUrl.value)

function buildParams() {
  const params = {}
  if (filters.status) params.status = filters.status
  if (filters.product_line) params.product_line = filters.product_line
  if (filters.topic) params.topic = filters.topic
  if (debouncedSearch.value) params.q = debouncedSearch.value
  return params
}

async function loadFacts() {
  loading.value = true
  try {
    const { data } = await brandVaultApi.facts(websiteId, buildParams())
    const body = data?.data || data || {}
    facts.value = body.results || body || []
    nextUrl.value = body.next || null
  } catch (e) {
    console.error('Failed to load facts', e)
    facts.value = []
    nextUrl.value = null
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const { data } = await brandVaultApi.stats(websiteId)
    const body = data?.data || data || {}
    const bs = body.by_status || {}
    stats.pending = bs.pending || 0
    stats.approved = bs.approved || 0
    stats.rejected = bs.rejected || 0
    stats.auto = bs.auto || 0
    productLines.value = Object.keys(body.by_product_line || {})
    topics.value = Object.keys(body.by_topic || {})
  } catch (e) {
    console.error('Failed to load stats', e)
  }
}

async function loadMore() {
  if (!nextUrl.value) return
  loadingMore.value = true
  try {
    // Use a simple page param fallback — backend uses paginated_response.
    // We re-call with offset query if next URL is present.
    const url = nextUrl.value
    const qs = url.includes('?') ? url.split('?')[1] : ''
    const params = Object.fromEntries(new URLSearchParams(qs))
    const { data } = await brandVaultApi.facts(websiteId, { ...buildParams(), ...params })
    const body = data?.data || data || {}
    facts.value = facts.value.concat(body.results || [])
    nextUrl.value = body.next || null
  } catch (e) {
    console.error('Load more failed', e)
  } finally {
    loadingMore.value = false
  }
}

async function onApprove(fact) {
  try {
    const { data } = await brandVaultApi.approve(fact.id)
    const updated = data?.data || data
    replaceFact(updated)
    toast.success('Fact approved.')
    loadStats()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not approve fact.')
  }
}

async function onReject(fact) {
  try {
    const { data } = await brandVaultApi.reject(fact.id)
    const updated = data?.data || data
    replaceFact(updated)
    toast.success('Fact rejected.')
    loadStats()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not reject fact.')
  }
}

function onEditClick(fact) {
  editFact.value = fact
  editOpen.value = true
}

function onEditSaved(newFact) {
  if (newFact) {
    facts.value.unshift(newFact)
  }
  loadStats()
  loadFacts()
}

function replaceFact(updated) {
  if (!updated?.id) return
  const idx = facts.value.findIndex((f) => f.id === updated.id)
  if (idx >= 0) facts.value.splice(idx, 1, updated)
}

async function onReExtract() {
  extracting.value = true
  try {
    await brandVaultApi.triggerExtract(websiteId)
    toast.success('Extraction queued. New facts will appear shortly.')
  } catch (e) {
    toast.error(e.displayMessage || 'Could not queue extraction.')
  } finally {
    extracting.value = false
  }
}

onMounted(() => {
  loadFacts()
  loadStats()
})

watch([
  () => filters.status,
  () => filters.product_line,
  () => filters.topic,
  debouncedSearch,
], loadFacts)
</script>

<style scoped>
.bv-filter {
  border-radius: 9999px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  outline: none;
  transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}
.bv-filter:hover {
  border-color: var(--border-hover);
}
.bv-filter:focus-visible {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px var(--brand-accent-glow);
}
</style>
