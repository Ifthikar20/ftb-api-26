<template>
  <div class="mx-auto max-w-7xl px-6 py-8">
    <!-- Header -->
    <header id="acc-header" class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight" style="color: var(--text-primary)">Accuracy</h1>
        <p v-if="websiteName" class="mt-1 text-sm" style="color: var(--text-secondary)">{{ websiteName }}</p>
      </div>
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
        <span class="hidden h-4 w-px sm:block" style="background: var(--border-color)" aria-hidden="true"></span>
        <select v-model="providerFilter" class="acc-filter">
          <option v-for="p in providerOptions" :key="p.value || 'all'" :value="p.value">
            {{ p.label }}
          </option>
        </select>
      </div>
    </header>

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
        v-if="accuracy.total_claims === 0"
        class="flex flex-col items-center justify-center rounded-3xl border border-dashed px-8 py-16 text-center"
        style="border-color: var(--border-color); background: var(--bg-card)"
      >
        <h2 class="text-lg font-semibold" style="color: var(--text-primary)">No claims tracked yet</h2>
        <p class="mt-2 max-w-md text-sm" style="color: var(--text-secondary)">
          Run an audit to start tracking accuracy.
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
        <!-- Stat row -->
        <section id="acc-stats" class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Total claims</AirCardSubtitle>
            <div class="mt-1 text-2xl font-semibold tabular-nums" style="color: var(--text-primary)">
              {{ accuracy.total_claims.toLocaleString() }}
            </div>
          </AirCard>
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Verified</AirCardSubtitle>
            <div class="mt-1 text-2xl font-semibold tabular-nums" style="color: var(--color-success)">
              {{ accuracy.verified.toLocaleString() }}
            </div>
          </AirCard>
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Mismatched</AirCardSubtitle>
            <div class="mt-1 text-2xl font-semibold tabular-nums" style="color: var(--color-danger)">
              {{ accuracy.mismatched.toLocaleString() }}
            </div>
          </AirCard>
          <AirCard size="md">
            <AirCardSubtitle class="text-xs uppercase tracking-wide">Accuracy rate</AirCardSubtitle>
            <div class="mt-1 flex items-baseline gap-1">
              <span class="text-2xl font-semibold tabular-nums" style="color: var(--text-primary)">
                {{ accuracyPct }}
              </span>
              <span class="text-sm" style="color: var(--text-muted)">%</span>
            </div>
          </AirCard>
        </section>

        <!-- Severity breakdown bar -->
        <AirCard id="acc-severity" size="md" class="mb-6">
          <h2 class="mb-3 text-sm font-semibold" style="color: var(--text-primary)">
            Mismatches by severity
          </h2>
          <div v-if="severityTotal === 0" class="text-xs" style="color: var(--text-muted)">
            No mismatches in this window.
          </div>
          <div v-else>
            <div class="flex h-3 w-full overflow-hidden rounded-full" style="background: var(--border-color)">
              <div
                v-for="seg in severitySegments"
                :key="seg.severity"
                class="h-full"
                :class="seg.bg"
                :style="{ width: seg.percent + '%' }"
                :title="`${seg.label}: ${seg.count} (${seg.percent}%)`"
              ></div>
            </div>
            <div class="mt-3 flex flex-wrap gap-3 text-xs">
              <span
                v-for="seg in severitySegments"
                :key="seg.severity + '-l'"
                class="inline-flex items-center gap-1.5"
              >
                <SeverityBadge :severity="seg.severity" />
                <span style="color: var(--text-muted)">{{ seg.count }}</span>
              </span>
            </div>
          </div>
        </AirCard>

        <!-- Trend chart -->
        <AirCard size="md" class="mb-8">
          <h2 class="mb-3 text-sm font-semibold" style="color: var(--text-primary)">
            Mismatches over time, by severity
          </h2>
          <div v-if="!trendData.length" class="text-xs" style="color: var(--text-muted)">
            Trend data will appear once more audits run.
          </div>
          <template v-else>
            <svg
              :viewBox="`0 0 ${trendWidth} ${trendHeight}`"
              class="h-32 w-full"
              preserveAspectRatio="none"
            >
              <path
                v-for="line in trendLines"
                :key="line.severity"
                :d="line.d"
                fill="none"
                :stroke="line.stroke"
                stroke-width="2"
              />
            </svg>
            <div class="mt-3 flex flex-wrap gap-3 text-xs">
              <span
                v-for="line in trendLines"
                :key="line.severity + '-leg'"
                class="inline-flex items-center gap-1.5"
              >
                <span class="inline-block h-2 w-3 rounded-sm" :style="{ background: line.stroke }"></span>
                <span class="capitalize" style="color: var(--text-secondary)">{{ line.severity }}</span>
              </span>
            </div>
          </template>
        </AirCard>

        <!-- Severity quick-filter chips -->
        <section class="mb-5 flex flex-wrap items-center gap-2">
          <AirChip
            as="button"
            :variant="mmFilters.severity === '' ? 'primary' : 'neutral'"
            size="sm"
            @click="mmFilters.severity = ''"
          >All</AirChip>
          <AirChip
            as="button"
            :variant="mmFilters.severity === 'critical' ? 'danger' : 'neutral'"
            size="sm"
            @click="mmFilters.severity = mmFilters.severity === 'critical' ? '' : 'critical'"
          >Critical</AirChip>
          <AirChip
            as="button"
            :variant="mmFilters.severity === 'high' ? 'danger' : 'neutral'"
            size="sm"
            @click="mmFilters.severity = mmFilters.severity === 'high' ? '' : 'high'"
          >High</AirChip>
          <AirChip
            as="button"
            :variant="mmFilters.severity === 'medium' ? 'warning' : 'neutral'"
            size="sm"
            @click="mmFilters.severity = mmFilters.severity === 'medium' ? '' : 'medium'"
          >Medium</AirChip>
          <AirChip
            as="button"
            :variant="mmFilters.severity === 'low' ? 'info' : 'neutral'"
            size="sm"
            @click="mmFilters.severity = mmFilters.severity === 'low' ? '' : 'low'"
          >Low</AirChip>
          <AirChip
            as="button"
            :variant="mmFilters.severity === 'info' ? 'neutral' : 'neutral'"
            size="sm"
            @click="mmFilters.severity = mmFilters.severity === 'info' ? '' : 'info'"
          >Info</AirChip>
          <span class="hidden h-4 w-px sm:block" style="background: var(--border-color)" aria-hidden="true"></span>
          <select v-model="mmFilters.type" class="acc-filter">
            <option value="">All types</option>
            <option v-for="t in mismatchTypes" :key="t" :value="t">{{ t }}</option>
          </select>
          <select v-model="mmFilters.product_line" class="acc-filter">
            <option value="">All product lines</option>
            <option v-for="pl in productLineOptions" :key="pl" :value="pl">{{ pl }}</option>
          </select>
          <input v-model="mmFilters.since" type="date" class="acc-filter" />
          <label class="inline-flex items-center gap-1.5 text-xs" style="color: var(--text-secondary)">
            <input v-model="mmFilters.includeDismissed" type="checkbox" />
            Show dismissed
          </label>
        </section>

        <!-- Mismatch list -->
        <section id="acc-mismatches">
          <div
            v-if="mismatchesLoading"
            class="rounded-2xl border p-6 text-center text-sm"
            style="border-color: var(--border-color); background: var(--bg-card); color: var(--text-muted)"
          >
            Loading mismatches...
          </div>
          <div
            v-else-if="!mismatches.length"
            class="rounded-3xl border border-dashed p-10 text-center text-sm"
            style="border-color: var(--border-color); background: var(--bg-card); color: var(--text-muted)"
          >
            No mismatches match these filters.
          </div>
          <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            <AirCard
              v-for="mm in mismatches"
              :key="mm.id"
              size="md"
              interactive
              :class="['flex h-full flex-col', mm.dismissed ? 'opacity-60' : '']"
              @click="openMismatch(mm)"
            >
              <div class="mb-3 flex flex-wrap items-center gap-2">
                <SeverityBadge :severity="mm.severity" />
                <AirChip variant="neutral" size="xs">{{ mm.mismatch_type || '—' }}</AirChip>
              </div>
              <p
                class="text-[15px] font-medium leading-snug line-clamp-3"
                :style="{
                  color: mm.dismissed ? 'var(--text-muted)' : 'var(--text-primary)',
                  textDecoration: mm.dismissed ? 'line-through' : 'none',
                }"
              >
                {{ mm.claim?.text || '—' }}
              </p>
              <p
                v-if="mm.dismissed && mm.dismissal_reason"
                class="mt-2 text-xs italic"
                style="color: var(--text-muted)"
              >
                Dismissed: {{ mm.dismissal_reason }}
              </p>
              <p
                v-if="mm.matched_fact"
                class="mt-2 line-clamp-2 text-xs"
                style="color: var(--text-secondary)"
              >
                <span class="font-medium" style="color: var(--text-primary)">Vault:</span>
                {{ mm.matched_fact.subject }} · {{ mm.matched_fact.predicate }} · {{ mm.matched_fact.object }}
              </p>
              <p v-else class="mt-2 text-xs italic" style="color: var(--text-muted)">
                No matching fact in vault
              </p>
              <div
                class="mt-auto flex items-center justify-between gap-2 pt-4"
                style="border-top: 1px solid var(--border-color)"
              >
                <div class="flex flex-col text-xs" style="color: var(--text-muted)">
                  <span>{{ mm.claim?.provider || '—' }}</span>
                  <span>{{ formatDate(mm.created_at) }}</span>
                </div>
                <AirButton variant="outline" size="sm" @click.stop="openMismatch(mm)">
                  View
                </AirButton>
              </div>
            </AirCard>
          </div>
          <div v-if="mismatches.length && mmHasMore" class="mt-6 flex justify-center">
            <AirButton
              variant="secondary"
              size="md"
              :loading="mmLoadingMore"
              :disabled="mmLoadingMore"
              @click="loadMoreMismatches"
            >
              {{ mmLoadingMore ? 'Loading...' : 'Load more' }}
            </AirButton>
          </div>
        </section>
      </template>
    </template>

    <MismatchDrawer
      v-model:open="drawerOpen"
      :mismatch="drawerMismatch"
      @dismissed="onDismissed"
    />

    <OnboardingTooltip storage-key="fb_tour_accuracy_v1" :steps="tourSteps" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import claimVerifierApi from '@/api/claimVerifier'
import SeverityBadge from '@/components/claim_verifier/SeverityBadge.vue'
import MismatchDrawer from '@/components/claim_verifier/MismatchDrawer.vue'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'
import AirButton from '@/components/ui/AirButton.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirCardSubtitle from '@/components/ui/AirCardSubtitle.vue'
import AirChip from '@/components/ui/AirChip.vue'

const route = useRoute()
const appStore = useAppStore()
const websiteId = route.params.websiteId

const websiteName = computed(() => appStore.activeWebsite?.name || '')

const periodOptions = [
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
]
const providerOptions = [
  { value: '', label: 'All providers' },
  { value: 'claude', label: 'Claude' },
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'perplexity', label: 'Perplexity' },
]

const periodDays = ref(30)
const providerFilter = ref('')

const loading = ref(true)
const accuracy = ref({
  total_claims: 0,
  verified: 0,
  mismatched: 0,
  accuracy_rate: 1,
  by_severity: {},
  by_type: {},
  by_provider: {},
  trend: [],
})

const mismatches = ref([])
const mismatchesLoading = ref(false)
const mmLoadingMore = ref(false)
const mmNextUrl = ref(null)

const mmFilters = reactive({
  severity: '',
  type: '',
  product_line: '',
  since: '',
  includeDismissed: false,
})

const drawerOpen = ref(false)
const drawerMismatch = ref(null)

const SEV_BG = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-amber-400',
  low: 'bg-blue-400',
  info: 'bg-slate-400',
}
const SEV_ORDER = ['critical', 'high', 'medium', 'low', 'info']

const tourSteps = [
  {
    target: '#acc-header',
    title: 'Accuracy',
    message: 'How accurate is what AI assistants say about you? This view tracks every claim against your Brand Vault.',
    position: 'bottom',
  },
  {
    target: '#acc-stats',
    title: 'Verified vs mismatched',
    message: 'Each claim is matched to your Brand Vault — verified ones support your story, mismatched ones flag risk.',
    position: 'bottom',
  },
  {
    target: '#acc-severity',
    title: 'Severity breakdown',
    message: 'Mismatches are scored by severity so you can prioritize the worst offenders first.',
    position: 'bottom',
  },
  {
    target: '#acc-mismatches',
    title: 'Inspect any mismatch',
    message: 'Click any mismatch to see the discrepancy side-by-side with your verified facts.',
    position: 'top',
  },
]

const accuracyPct = computed(() =>
  Math.round((Number(accuracy.value.accuracy_rate) || 0) * 1000) / 10,
)

const severityTotal = computed(() =>
  SEV_ORDER.reduce((acc, s) => acc + (accuracy.value.by_severity?.[s] || 0), 0),
)

const severitySegments = computed(() => {
  const total = severityTotal.value
  if (!total) return []
  return SEV_ORDER
    .map((sev) => {
      const count = accuracy.value.by_severity?.[sev] || 0
      return {
        severity: sev,
        count,
        percent: Math.round((count / total) * 1000) / 10,
        bg: SEV_BG[sev],
        label: sev.charAt(0).toUpperCase() + sev.slice(1),
      }
    })
    .filter((s) => s.count > 0)
})

const trendData = computed(() => accuracy.value.trend || [])
const trendWidth = 600
const trendHeight = 120
const SEV_STROKE = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#60a5fa',
  info: '#94a3b8',
}
const trendLines = computed(() => {
  const arr = trendData.value
  if (!arr.length) return []
  // Normalize: each entry may carry severity_breakdown (new) or claims (old).
  const series = SEV_ORDER.map((sev) => ({
    severity: sev,
    stroke: SEV_STROKE[sev],
    values: arr.map((d) => (d.severity_breakdown ? (d.severity_breakdown[sev] || 0) : 0)),
  }))
  const max = Math.max(1, ...series.flatMap((s) => s.values))
  return series.map((s) => {
    const pts = s.values.map((v, i) => {
      const x = arr.length === 1 ? trendWidth / 2 : (i / (arr.length - 1)) * trendWidth
      const y = trendHeight - (v / max) * (trendHeight - 10) - 5
      return `${x},${y}`
    })
    const d = pts.length ? 'M' + pts.join(' L') : ''
    return { severity: s.severity, stroke: s.stroke, d }
  })
})

const mismatchTypes = computed(() => Object.keys(accuracy.value.by_type || {}))
const productLineOptions = computed(() => {
  const set = new Set()
  for (const m of mismatches.value) {
    const pl = m.matched_fact?.product_line
    if (pl) set.add(pl)
  }
  return Array.from(set)
})

const mmHasMore = computed(() => !!mmNextUrl.value)

function buildAccuracyParams() {
  const p = { period_days: periodDays.value }
  if (providerFilter.value) p.provider = providerFilter.value
  return p
}

function buildMismatchParams() {
  const p = {}
  if (mmFilters.severity) p.severity = mmFilters.severity
  if (mmFilters.type) p.type = mmFilters.type
  if (mmFilters.product_line) p.product_line = mmFilters.product_line
  if (mmFilters.since) p.since = mmFilters.since
  if (mmFilters.includeDismissed) p.include_dismissed = '1'
  return p
}

async function loadAccuracy() {
  loading.value = true
  try {
    const { data } = await claimVerifierApi.accuracy(websiteId, buildAccuracyParams())
    accuracy.value = data?.data || data || accuracy.value
  } catch (e) {
    console.error('Accuracy load failed', e)
  } finally {
    loading.value = false
  }
}

async function loadMismatches() {
  mismatchesLoading.value = true
  try {
    const { data } = await claimVerifierApi.mismatches(websiteId, buildMismatchParams())
    const body = data?.data || data || {}
    mismatches.value = body.results || body || []
    mmNextUrl.value = body.next || null
  } catch (e) {
    console.error('Mismatches load failed', e)
    mismatches.value = []
    mmNextUrl.value = null
  } finally {
    mismatchesLoading.value = false
  }
}

async function loadMoreMismatches() {
  if (!mmNextUrl.value) return
  mmLoadingMore.value = true
  try {
    const qs = mmNextUrl.value.includes('?') ? mmNextUrl.value.split('?')[1] : ''
    const params = Object.fromEntries(new URLSearchParams(qs))
    const { data } = await claimVerifierApi.mismatches(websiteId, {
      ...buildMismatchParams(),
      ...params,
    })
    const body = data?.data || data || {}
    mismatches.value = mismatches.value.concat(body.results || [])
    mmNextUrl.value = body.next || null
  } catch (e) {
    console.error('Load more mismatches failed', e)
  } finally {
    mmLoadingMore.value = false
  }
}

function openMismatch(mm) {
  drawerMismatch.value = mm
  drawerOpen.value = true
}

function onDismissed(updated) {
  if (!updated?.id) return
  const idx = mismatches.value.findIndex((m) => m.id === updated.id)
  if (idx >= 0) {
    if (mmFilters.includeDismissed) {
      mismatches.value.splice(idx, 1, updated)
    } else {
      mismatches.value.splice(idx, 1)
    }
  }
}

function formatDate(v) {
  if (!v) return ''
  try {
    return new Date(v).toLocaleDateString()
  } catch {
    return v
  }
}

onMounted(() => {
  loadAccuracy()
  loadMismatches()
})

watch([periodDays, providerFilter], () => {
  loadAccuracy()
})
watch(
  [
    () => mmFilters.severity,
    () => mmFilters.type,
    () => mmFilters.product_line,
    () => mmFilters.since,
    () => mmFilters.includeDismissed,
  ],
  loadMismatches,
)
</script>

<style scoped>
.acc-filter {
  border-radius: 9999px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 0.4rem 0.8rem;
  font-size: 0.75rem;
  outline: none;
  transition: border-color 150ms ease-out, box-shadow 150ms ease-out;
}
.acc-filter:hover {
  border-color: var(--border-hover);
}
.acc-filter:focus-visible {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px var(--brand-accent-glow);
}
</style>
