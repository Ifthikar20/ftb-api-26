<template>
  <div class="mx-auto max-w-7xl px-6 py-8">
    <!-- Header -->
    <header id="pl-header" class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight" style="color: var(--text-primary)">
          Prompt Library
        </h1>
        <p class="mt-1 max-w-2xl text-sm" style="color: var(--text-secondary)">
          Describe a real-world scenario. We'll generate prompts that AI assistants
          are likely to be asked about you.
        </p>
      </div>
      <div class="flex items-center gap-2">
        <AirButton id="pl-new-btn" variant="primary" size="sm" @click="newPromptOpen = true">New prompt</AirButton>
        <AirButton variant="outline" size="sm" :loading="synthesizing" @click="onSynthesize">
          Generate 50 with DeepSeek
        </AirButton>
        <AirButton variant="ghost" size="sm" :disabled="!websiteId" @click="variablesOpen = true">
          Edit variables
        </AirButton>
      </div>
    </header>

    <!-- Context input -->
    <section class="mb-8">
      <ContextInputCard
        v-model="contextInput"
        :loading="generating"
        @generate="onGenerate"
      />
    </section>

    <!-- Generated results -->
    <section v-if="generatedPrompts.length || generationError" class="mb-10">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
        <h2 class="text-lg font-semibold" style="color: var(--text-primary)">
          {{ generatedPrompts.length }} results
          <span v-if="generationProvider" style="color: var(--text-muted); font-weight: 400">
            · {{ generationProvider }}
          </span>
        </h2>
        <AirButton variant="ghost" size="sm" :loading="generating" @click="regenerate">
          Search again
        </AirButton>
      </div>

      <div v-if="generatedPrompts.length" class="mb-3 flex flex-wrap items-center gap-2">
        <span class="pl-filter-label">Style:</span>
        <AirChip
          v-for="s in generatedStyleFilters"
          :key="'gs-' + s.value"
          as="button"
          size="sm"
          :variant="s.value === generatedStyleFilter ? 'primary' : 'neutral'"
          @click="generatedStyleFilter = s.value"
        >{{ s.label }}</AirChip>
      </div>

      <div
        v-if="generationError"
        class="rounded-3xl border border-dashed p-8 text-center text-sm"
        style="border-color: var(--border-color); background: var(--bg-card); color: var(--text-muted)"
      >
        We couldn't generate prompts for that context — try adding more detail.
      </div>

      <AirCard v-else size="md" :padded="false">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead>
              <tr style="border-bottom: 1px solid var(--border-color)">
                <th class="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted); width: 110px">Style</th>
                <th class="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted); width: 140px">Trend</th>
                <th class="px-3 py-3 text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">Prompt</th>
                <th class="px-3 py-3 text-right text-[11px] font-semibold uppercase tracking-wider" style="color: var(--text-muted); width: 130px">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in filteredGeneratedPrompts"
                :key="p._uid"
                class="pl-row"
                style="border-top: 1px solid var(--border-color)"
              >
                <td class="px-4 py-3 align-top">
                  <AirChip size="xs" variant="primary">{{ titleCaseStyle(p.style) }}</AirChip>
                </td>
                <td class="px-3 py-3 align-top">
                  <div class="flex items-center gap-2">
                    <div class="pl-trend-bar">
                      <div class="pl-trend-fill" :class="trendBarClass(p.trend_score)" :style="{ width: (p.trend_score || 0) + '%' }"></div>
                    </div>
                    <span class="text-xs tabular-nums" style="color: var(--text-secondary)">{{ p.trend_score ?? '—' }}</span>
                  </div>
                  <div class="mt-1 text-[10px] uppercase tracking-wider" style="color: var(--text-muted)">{{ trendLabel(p.trend_score) }}</div>
                </td>
                <td class="px-3 py-3 align-top" style="color: var(--text-primary)">
                  <div class="leading-snug" v-html="renderTemplate(p.template_text)"></div>
                </td>
                <td class="px-3 py-3 align-top text-right">
                  <AirButton
                    v-if="!p._saved"
                    variant="primary"
                    size="sm"
                    :loading="!!p._saving"
                    @click="onSaveGenerated(p)"
                  >
                    Save
                  </AirButton>
                  <AirChip v-else size="sm" variant="success">Saved</AirChip>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </AirCard>
    </section>

    <!-- Saved prompts browse -->
    <section v-if="websiteId" class="mb-2">
      <h2 class="mb-3 text-lg font-semibold" style="color: var(--text-primary)">My saved prompts</h2>
    </section>

    <!-- Industry strip (legacy filter aid) -->
    <section v-if="false" class="mb-6">
      <div class="mb-3 flex flex-wrap items-end gap-3">
        <div class="flex-1 min-w-[16rem]">
          <label class="pl-eyebrow">Industry</label>
          <select id="pl-industry" v-model="industrySlug" class="pl-control w-full">
            <option value="">Select an industry…</option>
            <option v-for="ind in industries" :key="ind.id" :value="ind.slug">{{ ind.name }}</option>
          </select>
        </div>
      </div>

      <AirCard v-if="industrySlug" size="md">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <AirCardSubtitle class="text-xs uppercase tracking-wide">
              Google Trends · {{ activeIndustryName }}
            </AirCardSubtitle>
            <div class="mt-1 text-base font-semibold" style="color: var(--text-primary)">
              <template v-if="trends?.keyword">"{{ trends.keyword }}"</template>
              <template v-else>—</template>
            </div>
            <p class="mt-1 text-xs" style="color: var(--text-secondary)">
              <template v-if="trends?.refreshed_at">12-month interest, refreshed {{ formatRelative(trends.refreshed_at) }}</template>
              <template v-else-if="trendsLoading">Fetching live trends…</template>
              <template v-else-if="trends?.error">Live trends unavailable</template>
              <template v-else>No trend data yet</template>
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <AirChip
              v-for="(g, i) in trends?.top_regions || []"
              :key="g.code + i"
              :variant="i === 0 ? 'primary' : 'neutral'"
              size="sm"
            >{{ g.name }} · {{ g.value }}</AirChip>
          </div>
        </div>
        <div class="mt-4">
          <Sparkline :values="(trends?.interest_over_time || []).map(p => p.value)" />
        </div>
      </AirCard>
    </section>

    <!-- Stat strip -->
    <section class="mb-6 grid gap-4 grid-cols-2 md:grid-cols-4">
      <AirCard size="sm"><div class="pl-stat-label">Total prompts</div><div class="pl-stat-val">{{ stats.total }}</div></AirCard>
      <AirCard size="sm"><div class="pl-stat-label">Active</div><div class="pl-stat-val">{{ stats.active }}</div></AirCard>
      <AirCard size="sm"><div class="pl-stat-label">Avg effectiveness</div><div class="pl-stat-val">{{ stats.avgEff }}</div></AirCard>
      <AirCard size="sm"><div class="pl-stat-label">Top-10 lift</div><div class="pl-stat-val">{{ stats.topLift }}</div></AirCard>
    </section>

    <!-- Filter bar -->
    <section id="pl-filters" class="mb-5 flex flex-wrap items-center gap-2">
      <span class="pl-filter-label">Style:</span>
      <AirChip
        v-for="s in styleFilters"
        :key="'st-' + s.value"
        as="button"
        size="sm"
        :variant="s.value === styleFilter ? 'primary' : 'neutral'"
        @click="styleFilter = s.value"
      >{{ s.label }}</AirChip>

      <span class="pl-divider"></span>
      <span class="pl-filter-label">Source:</span>
      <AirChip
        v-for="s in sourceFilters"
        :key="'sr-' + s.value"
        as="button"
        size="sm"
        :variant="s.value === sourceFilter ? 'primary' : 'neutral'"
        @click="sourceFilter = s.value"
      >{{ s.label }}</AirChip>

      <span class="pl-divider"></span>
      <span class="pl-filter-label">Effectiveness:</span>
      <AirChip
        v-for="e in effFilters"
        :key="'ef-' + e.value"
        as="button"
        size="sm"
        :variant="e.value === effFilter ? 'primary' : 'neutral'"
        @click="effFilter = e.value"
      >{{ e.label }}</AirChip>

      <span class="pl-divider"></span>
      <select v-model="sort" class="pl-control">
        <option value="effectiveness">Highest effectiveness</option>
        <option value="newest">Most recent</option>
        <option value="most_used">Most-used</option>
        <option value="untested">Untested first</option>
      </select>
      <input v-model="searchInput" type="search" placeholder="Search prompts…" class="pl-control w-56" />
      <span class="ml-auto text-xs" style="color: var(--text-muted)">
        {{ filteredPrompts.length }} prompts shown
      </span>
    </section>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
      <AirCard v-for="i in 6" :key="i" size="md">
        <div class="pl-skeleton-row" style="width: 35%"></div>
        <div class="pl-skeleton-row mt-3"></div>
        <div class="pl-skeleton-row" style="width: 80%"></div>
        <div class="pl-skeleton-row mt-3" style="width: 30%"></div>
      </AirCard>
    </div>

    <!-- Empty: saved prompts list -->
    <div
      v-else-if="!prompts.length && websiteId"
      class="rounded-3xl border border-dashed p-8 text-center text-sm"
      style="border-color: var(--border-color); background: var(--bg-card); color: var(--text-muted)"
    >
      Your saved prompts will appear here.
    </div>

    <!-- Legacy empty -->
    <div
      v-else-if="false && !prompts.length"
      class="flex flex-col items-center justify-center rounded-3xl border border-dashed px-8 py-16 text-center"
      style="border-color: var(--border-color); background: var(--bg-card)"
    >
      <h3 class="text-lg font-semibold" style="color: var(--text-primary)">Let's seed your first 50 prompts</h3>
      <p class="mt-2 max-w-md text-sm" style="color: var(--text-secondary)">
        Generate a starter pack with DeepSeek for this industry, or write your own.
      </p>
      <div class="mt-4 flex gap-2">
        <AirButton variant="primary" :loading="synthesizing" @click="onSynthesize">Generate 50 with DeepSeek</AirButton>
        <AirButton variant="outline" @click="newPromptOpen = true">Write your own</AirButton>
      </div>
    </div>

    <!-- Empty: filtered out -->
    <div
      v-else-if="!filteredPrompts.length"
      class="rounded-3xl border border-dashed p-10 text-center text-sm"
      style="border-color: var(--border-color); background: var(--bg-card); color: var(--text-muted)"
    >
      No prompts match these filters. Try widening filters.
    </div>

    <!-- Card grid -->
    <div v-else class="grid gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
      <PromptCard
        v-for="(p, idx) in pagedPrompts"
        :id="idx === 0 ? 'pl-first-card' : null"
        :key="p.id"
        :prompt="p"
        :variables="resolvedVariables"
        @select="onSelect"
        @preview="onPreview"
        @edit="onEdit"
        @smoke-test="onSmokeTest"
        @disable="onToggleActive"
        @delete="onDelete"
        @request-edit-variables="variablesOpen = true"
      />
    </div>

    <!-- Load more -->
    <div v-if="filteredPrompts.length > pageSize * page" class="mt-6 flex justify-center">
      <AirButton variant="ghost" size="sm" @click="page++">Load more</AirButton>
    </div>

    <!-- Slide-out + modal -->
    <VariablesPanel
      v-model="variablesOpen"
      :website-id="websiteId"
      :website-name="activeWebsiteName"
      @saved="onVariablesSaved"
    />
    <NewPromptModal
      v-model="newPromptOpen"
      :website-id="websiteId"
      :variables="resolvedVariables"
      @created="onPromptCreated"
    />

    <!-- Smoke-test result modal -->
    <BaseModal v-model="smokeOpen" title="Smoke test" subtitle="Single-provider sanity run" wide>
      <SmokeTestResult v-if="smokeResult" :result="smokeResult" @try-provider="(p) => runSmoke(activeSmokePromptId, p)" />
      <div v-else class="text-sm" style="color: var(--text-muted)">Running…</div>
    </BaseModal>

    <OnboardingTooltip storage-key="fb_tour_prompt_library_v2" :steps="tourSteps" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, h } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useToast } from '@/composables/useToast'
import { useAppStore } from '@/stores/app'
import promptLibrary from '@/api/promptLibrary'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirCardSubtitle from '@/components/ui/AirCardSubtitle.vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import PromptCard from '@/components/prompt_library/PromptCard.vue'
import ContextInputCard from '@/components/prompt_library/ContextInputCard.vue'
import VariablesPanel from '@/components/prompt_library/VariablesPanel.vue'
import NewPromptModal from '@/components/prompt_library/NewPromptModal.vue'
import SmokeTestResult from '@/components/prompt_library/SmokeTestResult.vue'

const route = useRoute()
const toast = useToast()
const appStore = useAppStore()
const { activeWebsite } = storeToRefs(appStore)

const websiteId = computed(() => route.params.websiteId || activeWebsite.value?.id || null)
const activeWebsiteName = computed(() => activeWebsite.value?.name || '')

const industries = ref([])
const industrySlug = ref('')
const prompts = ref([])
const loading = ref(false)
const trends = ref(null)
const trendsLoading = ref(false)

const styleFilter = ref('')
const sourceFilter = ref('')
const effFilter = ref('')
const sort = ref('effectiveness')
const searchInput = ref('')
const debouncedSearch = ref('')
let searchTimer = null
watch(searchInput, (v) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { debouncedSearch.value = v }, 250)
})

const page = ref(1)
const pageSize = 24

const newPromptOpen = ref(false)
const variablesOpen = ref(false)
const smokeOpen = ref(false)
const smokeResult = ref(null)
const activeSmokePromptId = ref(null)
const synthesizing = ref(false)

// ── Context-driven generation state ──
const contextInput = ref('')
const generating = ref(false)
const generatedPrompts = ref([]) // { _uid, _saved, _saving, template_text, ... }
const generationProvider = ref('')
const generationError = ref(false)
const generatedStyleFilter = ref('')
const generatedStyleFilters = [
  { value: '', label: 'All' },
  { value: 'story', label: 'Story' },
  { value: 'question', label: 'Question' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'local', label: 'Local' },
  { value: 'how_to', label: 'How-to' },
]

const filteredGeneratedPrompts = computed(() => {
  if (!generatedStyleFilter.value) return generatedPrompts.value
  return generatedPrompts.value.filter(p => p.style === generatedStyleFilter.value)
})

function trendBarClass(score) {
  const s = Number(score) || 0
  if (s >= 70) return 'is-hot'
  if (s >= 40) return 'is-warm'
  return 'is-cool'
}

function trendLabel(score) {
  const s = Number(score) || 0
  if (s >= 70) return 'Trending'
  if (s >= 40) return 'Steady'
  return 'Niche'
}

function titleCaseStyle(value) {
  if (!value) return 'Question'
  const map = { story: 'Story', question: 'Question', comparison: 'Comparison', local: 'Local', how_to: 'How-to', listicle: 'Listicle', problem: 'Problem' }
  return map[value] || (String(value).charAt(0).toUpperCase() + String(value).slice(1))
}

function _escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderTemplate(template) {
  if (!template) return ''
  return _escapeHtml(template).replace(
    /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g,
    (_m, name) => `<span class="pl-var-chip">${_escapeHtml(name)}</span>`
  )
}

let _genUid = 0
function _wrap(item) {
  _genUid += 1
  return {
    _uid: 'g' + _genUid,
    _saved: false,
    _saving: false,
    is_active: true,
    ...item,
  }
}

async function onGenerate(text) {
  generating.value = true
  generationError.value = false
  try {
    const { data } = await promptLibrary.generateFromContext({
      context: text,
      count: 20,
      persist: false,
    })
    const payload = data?.data || data || {}
    const items = Array.isArray(payload.generated) ? payload.generated : []
    generatedPrompts.value = items.map(_wrap)
    generationProvider.value = payload.provider || ''
    if (!items.length) generationError.value = true
  } catch (e) {
    generatedPrompts.value = []
    generationProvider.value = ''
    generationError.value = true
    toast.error(e.displayMessage || 'Generation failed.')
  } finally {
    generating.value = false
  }
}

function regenerate() {
  if (!contextInput.value || generating.value) return
  onGenerate(contextInput.value.trim())
}

async function onSaveGenerated(prompt) {
  if (!websiteId.value) {
    toast.error('Pick a website first to save prompts.')
    return
  }
  prompt._saving = true
  try {
    const payload = {
      template_text: prompt.template_text,
      style: prompt.style,
      intent_bucket: prompt.intent_bucket,
      text: prompt.preview_text || prompt.template_text,
    }
    const { data } = await promptLibrary.savePromptToWebsite(websiteId.value, payload)
    const saved = data?.data || data
    prompt._saved = true
    prompt._savedId = saved?.id || null
    toast.success('Saved to your prompts.')
    loadPrompts()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not save.')
  } finally {
    prompt._saving = false
  }
}

function onRemoveGenerated(prompt) {
  // Local-only: drop from the saved-state UI; persisted row stays in DB.
  prompt._saved = false
}

const variablesMap = ref({})  // { name: value }

const styleFilters = [
  { value: '', label: 'All' },
  { value: 'story', label: 'Story' },
  { value: 'question', label: 'Question' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'local', label: 'Local' },
  { value: 'how_to', label: 'How-to' },
  { value: 'listicle', label: 'Listicle' },
]
const sourceFilters = [
  { value: '', label: 'All' },
  { value: 'manual', label: 'Manual' },
  { value: 'reddit', label: 'Reddit' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'claude', label: 'Claude' },
  { value: 'gsc', label: 'GSC' },
]
const effFilters = [
  { value: '', label: 'All' },
  { value: 'top', label: 'Top' },
  { value: 'underperforming', label: 'Underperforming' },
  { value: 'untested', label: 'Untested' },
]

const tourSteps = [
  {
    target: '#pl-header',
    title: 'Demand-side prompts',
    message: 'These are the real questions users ask AI assistants in your category.',
    position: 'bottom',
  },
  {
    target: '#pl-first-card',
    title: 'Effectiveness score',
    message: "Computed from past audits. Untested means we need 3+ runs to give a reliable number.",
    position: 'top',
  },
  {
    target: '#pl-first-card',
    title: 'Variables',
    message: "Slots like {{ industry }} are filled with your business data. Click 'Edit variables' to manage them.",
    position: 'top',
  },
  {
    target: '#pl-new-btn',
    title: 'Add your own',
    message: 'Add custom templates or generate 50 starter prompts with DeepSeek.',
    position: 'left',
  },
]

const activeIndustryName = computed(
  () => industries.value.find((i) => i.slug === industrySlug.value)?.name || '',
)

const resolvedVariables = computed(() => variablesMap.value || {})

const stats = computed(() => {
  const list = prompts.value
  const total = list.length
  const active = list.filter(p => p.is_active !== false).length
  const scored = list.filter(p => (p.effectiveness_components?.stable) || (p.runs_count || 0) >= 3)
  const avg = scored.length
    ? scored.reduce((s, p) => s + (p.effectiveness_score || 0), 0) / scored.length
    : 0
  const topLift = scored.filter(p => (p.effectiveness_score || 0) >= 0.7).length
  return {
    total,
    active,
    avgEff: scored.length ? Math.round(avg * 100) + '%' : '—',
    topLift: scored.length ? `${topLift}/${scored.length}` : '—',
  }
})

const filteredPrompts = computed(() => {
  let list = prompts.value
  if (styleFilter.value) list = list.filter(p => p.style === styleFilter.value)
  if (sourceFilter.value) list = list.filter(p => p.source === sourceFilter.value)
  if (effFilter.value === 'top') list = list.filter(p => (p.effectiveness_score || 0) >= 0.7 && (p.effectiveness_components?.stable))
  else if (effFilter.value === 'underperforming') list = list.filter(p => (p.effectiveness_components?.stable) && (p.effectiveness_score || 0) < 0.4)
  else if (effFilter.value === 'untested') list = list.filter(p => !(p.effectiveness_components?.stable) && (p.runs_count || 0) < 3)

  const sorted = [...list]
  if (sort.value === 'effectiveness') {
    sorted.sort((a, b) => (b.effectiveness_score || 0) - (a.effectiveness_score || 0))
  } else if (sort.value === 'newest') {
    sorted.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
  } else if (sort.value === 'most_used') {
    sorted.sort((a, b) => (b.runs_count || 0) - (a.runs_count || 0))
  } else if (sort.value === 'untested') {
    sorted.sort((a, b) => (a.runs_count || 0) - (b.runs_count || 0))
  }
  return sorted
})

const pagedPrompts = computed(() => filteredPrompts.value.slice(0, page.value * pageSize))

watch([styleFilter, sourceFilter, effFilter, sort, debouncedSearch], () => { page.value = 1 })

async function loadIndustries() {
  try {
    const { data } = await promptLibrary.getIndustries()
    industries.value = data?.results || data?.data || data || []
  } catch { industries.value = [] }
}

async function loadPrompts() {
  // Only show prompts the user has explicitly saved into THIS website's
  // set — the global library contains thousands of mined Reddit / synth
  // candidates that aren't relevant until the user picks them.
  if (!websiteId.value) {
    prompts.value = []
    loading.value = false
    return
  }
  loading.value = true
  try {
    const { data } = await promptLibrary.listBrandPrompts(websiteId.value)
    const rows = data?.data?.results || data?.results || data?.data || data || []
    const list = Array.isArray(rows) ? rows : []
    // The brand-prompts endpoint returns either {brand_prompt, prompt} or
    // a flat Prompt row — normalise to a flat shape the table expects.
    prompts.value = list.map(item => item.prompt ? { ...item.prompt, _brand_prompt_id: item.id } : item)
  } catch { prompts.value = [] }
  finally { loading.value = false }
}

async function loadTrends() {
  if (!industrySlug.value) { trends.value = null; return }
  trendsLoading.value = true
  try {
    const { data } = await promptLibrary.getIndustryTrends(industrySlug.value)
    trends.value = data?.data || data || null
  } catch { trends.value = null }
  finally { trendsLoading.value = false }
}

async function loadVariables() {
  if (!websiteId.value) { variablesMap.value = {}; return }
  try {
    const { data } = await promptLibrary.getVariables(websiteId.value)
    const payload = data?.data || data || {}
    variablesMap.value = payload.variables || {}
    // Merge auto provenance values into the resolved map for card display.
    if (Array.isArray(payload.provenance)) {
      const merged = { ...variablesMap.value }
      for (const r of payload.provenance) {
        if (r.value && !(r.name in merged)) merged[r.name] = r.value
      }
      variablesMap.value = merged
    }
  } catch { variablesMap.value = {} }
}

function onVariablesSaved(vars) {
  variablesMap.value = { ...variablesMap.value, ...vars }
}

async function onPreview(prompt) {
  try {
    const { data } = await promptLibrary.preview(prompt.id, websiteId.value)
    const p = data?.data || data || {}
    toast.success(p.filled_text ? `Preview: ${(p.filled_text || '').slice(0, 80)}…` : 'Previewed.')
  } catch (e) { toast.error(e.displayMessage || 'Preview failed.') }
}

function onSelect() { /* no-op for now */ }
function onEdit() { newPromptOpen.value = true }

async function runSmoke(promptId, provider = 'claude') {
  if (!websiteId.value) { toast.error('Pick a website first.'); return }
  smokeResult.value = null
  smokeOpen.value = true
  activeSmokePromptId.value = promptId
  try {
    const { data } = await promptLibrary.smokeTest(promptId, { provider, website_id: websiteId.value })
    smokeResult.value = data?.data || data
  } catch (e) {
    smokeResult.value = { error: e.displayMessage || 'Smoke test failed.', provider }
  }
}
function onSmokeTest(prompt) { runSmoke(prompt.id) }

async function onToggleActive(prompt) {
  try {
    const fn = prompt.is_active === false ? promptLibrary.enable : promptLibrary.disable
    await fn(prompt.id)
    prompt.is_active = !(prompt.is_active === false ? false : true) ? true : !prompt.is_active
    toast.success('Updated.')
    loadPrompts()
  } catch (e) { toast.error(e.displayMessage || 'Could not toggle.') }
}

async function onDelete(prompt) {
  if (!confirm('Delete this prompt? This cannot be undone.')) return
  try {
    await promptLibrary.disable(prompt.id)
    prompts.value = prompts.value.filter(p => p.id !== prompt.id)
    toast.success('Deleted.')
  } catch (e) { toast.error(e.displayMessage || 'Could not delete.') }
}

function onPromptCreated() { loadPrompts() }

async function onSynthesize() {
  if (!industrySlug.value) { toast.error('Pick an industry first.'); return }
  const ind = industries.value.find(i => i.slug === industrySlug.value)
  if (!ind) return
  synthesizing.value = true
  try {
    await promptLibrary.synthesize({ industry_id: ind.id, count: 50 })
    toast.success('Synthesizing 50 prompts — refresh in a moment.')
    setTimeout(loadPrompts, 1500)
  } catch (e) {
    toast.error(e.displayMessage || 'Synthesis failed.')
  } finally {
    synthesizing.value = false
  }
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

const Sparkline = {
  props: { values: { type: Array, default: () => [] } },
  setup(props) {
    return () => {
      const v = props.values
      if (!v.length) return h('span', { style: 'color: var(--text-muted); font-size: 11px' }, 'No trend data yet')
      const w = 720, ht = 56
      const max = Math.max(...v), min = Math.min(...v)
      const range = Math.max(1, max - min)
      const pts = v.map((val, i) => {
        const x = (i / Math.max(1, v.length - 1)) * w
        const y = ht - ((val - min) / range) * (ht - 6) - 3
        return `${x.toFixed(1)},${y.toFixed(1)}`
      }).join(' ')
      return h('svg', { width: '100%', height: ht, viewBox: `0 0 ${w} ${ht}`, preserveAspectRatio: 'none', style: 'display:block' },
        [h('polyline', { points: pts, fill: 'none', stroke: 'var(--brand-accent)', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })])
    }
  },
}

onMounted(async () => {
  await loadIndustries()
  await loadVariables()
  await loadPrompts()
})

watch([industrySlug, debouncedSearch], loadPrompts)
watch(industrySlug, loadTrends)
watch(websiteId, loadVariables)
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
}
.pl-control:focus-visible { border-color: var(--brand-accent); box-shadow: 0 0 0 3px var(--brand-accent-glow); }
.pl-eyebrow { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 4px; }
.pl-filter-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.pl-divider { display: inline-block; width: 1px; height: 16px; background: var(--border-color); margin: 0 6px; }
.pl-stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.pl-stat-val { font-size: 22px; font-weight: 600; color: var(--text-primary); margin-top: 4px; font-variant-numeric: tabular-nums; }
.pl-skeleton-row {
  height: 12px; border-radius: 6px;
  background: var(--border-color); opacity: 0.5;
  animation: pl-pulse 1.4s ease-in-out infinite;
}
@keyframes pl-pulse { 0%, 100% { opacity: 0.4 } 50% { opacity: 0.7 } }

.pl-stagger-enter-active { transition: opacity 0.35s ease, transform 0.35s ease; }
.pl-stagger-enter-from { opacity: 0; transform: translateY(8px); }
.pl-stagger-enter-to { opacity: 1; transform: translateY(0); }
.pl-stagger-leave-active { transition: opacity 0.2s ease; }
.pl-stagger-leave-to { opacity: 0; }

.pl-row { transition: background 0.12s ease-out; }
.pl-row:hover { background: var(--bg-surface, rgba(0, 0, 0, 0.02)); }

.pl-untested {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 9999px;
  border: 1px dashed var(--border-color);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
}

.pl-trend-bar {
  position: relative;
  width: 70px;
  height: 6px;
  border-radius: 9999px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.06));
  overflow: hidden;
}
.pl-trend-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease-out;
}
.pl-trend-fill.is-hot { background: var(--color-success, #10b981); }
.pl-trend-fill.is-warm { background: var(--brand-accent); }
.pl-trend-fill.is-cool { background: var(--text-muted); }

:deep(.pl-var-chip) {
  display: inline-block;
  padding: 1px 8px;
  margin: 0 2px;
  border-radius: 9999px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.04));
  color: var(--brand-accent);
  font-size: 0.8em;
  font-weight: 500;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  line-height: 1.3;
  vertical-align: baseline;
}
</style>
