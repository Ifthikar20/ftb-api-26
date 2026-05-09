<template>
  <div class="p-6">
    <!-- Header -->
    <header id="bv-header" class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900">Brand Vault</h1>
        <p v-if="websiteName" class="text-sm text-gray-500">{{ websiteName }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="rounded-md border border-indigo-600 bg-white px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
          @click="importOpen = true"
        >
          Import facts
        </button>
        <button
          class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          :disabled="extracting"
          @click="onReExtract"
        >
          {{ extracting ? 'Queuing...' : 'Re-extract from sources' }}
        </button>
      </div>
    </header>

    <!-- Stats row -->
    <section id="bv-stats" class="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <div class="rounded-lg border border-gray-200 bg-white p-4">
        <div class="text-xs text-gray-500">Pending review</div>
        <div class="mt-1 text-2xl font-semibold text-amber-700">{{ stats.pending }}</div>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4">
        <div class="text-xs text-gray-500">Approved</div>
        <div class="mt-1 text-2xl font-semibold text-emerald-700">{{ stats.approved }}</div>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4">
        <div class="text-xs text-gray-500">Rejected</div>
        <div class="mt-1 text-2xl font-semibold text-zinc-700">{{ stats.rejected }}</div>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4">
        <div class="text-xs text-gray-500">Auto-approved</div>
        <div class="mt-1 text-2xl font-semibold text-blue-700">{{ stats.auto }}</div>
      </div>
    </section>

    <!-- Filter bar -->
    <section id="bv-filters" class="mb-4 flex flex-wrap items-center gap-2">
      <select
        v-model="filters.status"
        class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-sm"
      >
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="auto">Auto-approved</option>
      </select>
      <select
        v-model="filters.product_line"
        class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-sm"
      >
        <option value="">All product lines</option>
        <option v-for="pl in productLines" :key="pl" :value="pl">{{ pl }}</option>
      </select>
      <select
        v-model="filters.topic"
        class="rounded-md border border-gray-200 bg-white px-2 py-1.5 text-sm"
      >
        <option value="">All topics</option>
        <option v-for="t in topics" :key="t" :value="t">{{ t }}</option>
      </select>
      <input
        v-model="searchInput"
        type="search"
        placeholder="Search facts..."
        class="ml-auto w-64 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm"
      />
    </section>

    <!-- Facts table -->
    <section class="rounded-lg border border-gray-200 bg-white">
      <div v-if="loading" class="p-8 text-center text-sm text-gray-500">Loading facts...</div>
      <div
        v-else-if="!facts.length"
        class="p-10 text-center text-sm text-gray-500"
      >
        No facts yet. Click <strong>Re-extract</strong> to mine your knowledge base.
      </div>
      <table v-else class="w-full text-left">
        <thead class="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
          <tr>
            <th class="px-3 py-2">Subject</th>
            <th class="px-3 py-2">Predicate</th>
            <th class="px-3 py-2">Object</th>
            <th class="px-3 py-2">Confidence</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2">Source</th>
            <th class="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          <FactRow
            v-for="fact in facts"
            :key="fact.id"
            :fact="fact"
            @approve="onApprove"
            @reject="onReject"
            @edit-click="onEditClick"
          />
        </tbody>
      </table>
      <div
        v-if="facts.length && hasMore"
        class="flex justify-center border-t border-gray-100 px-3 py-3"
      >
        <button
          class="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm hover:bg-gray-50"
          :disabled="loadingMore"
          @click="loadMore"
        >
          {{ loadingMore ? 'Loading...' : 'Load more' }}
        </button>
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
