<template>
  <div class="mx-auto max-w-7xl px-6 py-10">
    <!-- Header -->
    <header id="pl-header" class="mb-8 text-center">
      <h1 class="pl-hero-title">Prompt Library</h1>
      <p class="pl-hero-sub">
        Describe a scenario. We'll find the prompts AI assistants are likely
        being asked about you.
      </p>
    </header>

    <!-- Context input -->
    <section class="mb-10">
      <ContextInputCard
        v-model="contextInput"
        :loading="generating"
        @generate="onGenerate"
      />
    </section>

    <!-- Generated results -->
    <section class="mb-10">
      <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
        <h2 class="text-lg font-semibold" style="color: var(--text-primary)">
          <template v-if="generatedPrompts.length">
            {{ generatedPrompts.length }} results
            <span v-if="generationProvider" style="color: var(--text-muted); font-weight: 400">
              · {{ generationProvider }}
            </span>
          </template>
          <template v-else>
            Results
          </template>
        </h2>
        <AirButton
          v-if="generatedPrompts.length"
          variant="ghost"
          size="sm"
          :loading="generating"
          @click="regenerate"
        >
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

      <AirCard size="md" :padded="false">
        <div class="overflow-x-auto">
          <table class="pl-data-table">
            <thead>
              <tr>
                <th class="pl-th sortable" style="width: 110px" @click="toggleResultsSort('id')">
                  <div class="pl-th-inner">
                    <span>ID</span>
                    <SortIcon :state="resultsSortState('id')" />
                  </div>
                </th>
                <th class="pl-th sortable" style="width: 120px" @click="toggleResultsSort('style')">
                  <div class="pl-th-inner">
                    <span>Style</span>
                    <SortIcon :state="resultsSortState('style')" />
                  </div>
                </th>
                <th class="pl-th">
                  <div class="pl-th-inner">
                    <span>Prompt</span>
                  </div>
                </th>
                <th class="pl-th sortable" style="width: 200px" @click="toggleResultsSort('trend')">
                  <div class="pl-th-inner">
                    <span>Trend</span>
                    <span class="pl-info-icon" @click.stop role="button" tabindex="0" aria-label="How is trend scored?">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 16v-4M12 8h.01" stroke-linecap="round"/>
                      </svg>
                      <span class="pl-tooltip">
                        <strong>How we rank Trend</strong>
                        <p>A 0-100 score combining four signals:</p>
                        <ul>
                          <li><b>Search demand</b> — Google Trends-style interest for the question pattern in your category.</li>
                          <li><b>Currency</b> — recency-weighted, so seasonal and just-now-trending questions surface higher.</li>
                          <li><b>AI-assistant frequency</b> — how often LLMs receive this style of question (model-side telemetry).</li>
                          <li><b>Category fit</b> — match to your industry / location signals.</li>
                        </ul>
                        <p class="pl-tooltip-foot">Trending ≥ 70 · Steady 40-69 · Niche &lt; 40</p>
                      </span>
                    </span>
                    <SortIcon :state="resultsSortState('trend')" />
                  </div>
                </th>
                <th class="pl-th sortable" style="width: 140px" @click="toggleResultsSort('status')">
                  <div class="pl-th-inner">
                    <span>Status</span>
                    <SortIcon :state="resultsSortState('status')" />
                  </div>
                </th>
                <th class="pl-th text-right" style="width: 130px">
                  <div class="pl-th-inner justify-end">
                    <span>Action</span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!generatedPrompts.length" class="pl-empty-row">
                <td colspan="6">
                  <div class="pl-empty-state">
                    <div class="pl-empty-icon" aria-hidden="true">
                      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="11" cy="11" r="7" stroke-linecap="round"/>
                        <path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
                      </svg>
                    </div>
                    <div v-if="generating" class="pl-empty-title">Searching…</div>
                    <div v-else-if="generationError" class="pl-empty-title">No prompts for that scenario</div>
                    <div v-else class="pl-empty-title">No prompts yet</div>
                    <div class="pl-empty-sub">
                      <template v-if="generating">Generating natural-feeling prompts based on your scenario.</template>
                      <template v-else-if="generationError">Try adding a few more words or a specific place.</template>
                      <template v-else>Type a scenario above and hit Search to populate this table.</template>
                    </div>
                  </div>
                </td>
              </tr>
              <template v-for="(p, idx) in pagedGeneratedPrompts" :key="p._uid">
                <tr
                  class="pl-row"
                  :class="{ 'is-expanded': expandedResult === p._uid }"
                  @click="toggleExpand(p._uid)"
                >
                  <td class="pl-td">
                    <span class="pl-id-pill">{{ formatRowId(p) }}</span>
                  </td>
                  <td class="pl-td">
                    <AirChip size="xs" variant="neutral">{{ titleCaseStyle(p.style) }}</AirChip>
                  </td>
                  <td class="pl-td pl-td-prompt">
                    <span class="pl-prompt-text">{{ p.prompt_text || p.template_text }}</span>
                  </td>
                  <td class="pl-td">
                    <div class="flex items-center gap-2">
                      <div class="pl-trend-bar">
                        <div class="pl-trend-fill" :class="trendBarClass(p.trend_score)" :style="{ width: (p.trend_score || 0) + '%' }"></div>
                      </div>
                      <span class="text-xs tabular-nums" style="color: var(--text-secondary); min-width: 1.75rem">{{ p.trend_score ?? '—' }}</span>
                      <span class="text-[10px] uppercase tracking-wider" style="color: var(--text-muted)">{{ trendLabel(p.trend_score) }}</span>
                    </div>
                  </td>
                  <td class="pl-td">
                    <span v-if="p._saved" class="pl-status-pill is-signed">Saved</span>
                    <span v-else class="pl-status-pill is-pending">Untested</span>
                  </td>
                  <td class="pl-td text-right" @click.stop>
                    <div class="pl-action-row">
                      <AirButton
                        v-if="!p._saved"
                        variant="primary"
                        size="sm"
                        :loading="!!p._saving"
                        @click="onSaveGenerated(p)"
                      >
                        Save
                      </AirButton>
                      <button class="pl-expand-toggle" :aria-expanded="expandedResult === p._uid" @click.stop="toggleExpand(p._uid)" aria-label="Toggle details">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" :style="{ transform: expandedResult === p._uid ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.18s' }">
                          <path d="M6 9l6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="expandedResult === p._uid" class="pl-detail-row">
                  <td colspan="6" class="pl-detail-cell">
                    <div class="pl-detail-grid">
                      <div class="pl-detail-block">
                        <div class="pl-detail-label">Source</div>
                        <div class="pl-detail-value">{{ generationProvider || 'deepseek' }}</div>
                      </div>
                      <div class="pl-detail-block">
                        <div class="pl-detail-label">Intent</div>
                        <div class="pl-detail-value">{{ titleCaseStyle(p.intent_bucket) }}</div>
                      </div>
                      <div class="pl-detail-block">
                        <div class="pl-detail-label">Style</div>
                        <div class="pl-detail-value">{{ titleCaseStyle(p.style) }}</div>
                      </div>
                      <div class="pl-detail-block">
                        <div class="pl-detail-label">Words</div>
                        <div class="pl-detail-value">{{ wordCountOf(p) }}</div>
                      </div>
                      <div class="pl-detail-block">
                        <div class="pl-detail-label">Trend score</div>
                        <div class="pl-detail-value">{{ p.trend_score ?? '—' }} / 100 · <span style="color: var(--text-muted)">{{ trendLabel(p.trend_score) }}</span></div>
                      </div>
                      <div class="pl-detail-block">
                        <div class="pl-detail-label">Variables</div>
                        <div class="pl-detail-value">
                          <span v-if="!p.template_variables || !p.template_variables.length" style="color: var(--text-muted)">None — fully concrete</span>
                          <span v-else>
                            <AirChip v-for="v in p.template_variables" :key="v" size="xs" variant="info" class="mr-1">{{ v }}</AirChip>
                          </span>
                        </div>
                      </div>
                    </div>
                    <div class="pl-detail-prompt">
                      <div class="pl-detail-label mb-1">Full prompt</div>
                      <p class="pl-detail-fulltext">{{ p.prompt_text || p.template_text }}</p>
                    </div>
                    <div class="pl-detail-actions">
                      <AirButton variant="ghost" size="sm" @click.stop="onRemoveGenerated(p)">Skip</AirButton>
                      <AirButton
                        v-if="!p._saved"
                        variant="primary"
                        size="sm"
                        :loading="!!p._saving"
                        @click.stop="onSaveGenerated(p)"
                      >
                        Save to my prompts
                      </AirButton>
                      <AirChip v-else size="sm" variant="success">Saved</AirChip>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div v-if="generatedPrompts.length" class="pl-table-footer">
          <span class="pl-table-foot-info">
            Showing
            <strong>{{ resultsRangeStart }}-{{ resultsRangeEnd }}</strong>
            of {{ filteredGeneratedPrompts.length }}
          </span>
          <div class="pl-pagination">
            <button class="pl-page-btn" :disabled="resultsPage === 1" @click="resultsPage = Math.max(1, resultsPage - 1)" aria-label="Previous page">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <button class="pl-page-btn" :disabled="resultsPage >= resultsPageCount" @click="resultsPage = Math.min(resultsPageCount, resultsPage + 1)" aria-label="Next page">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
        </div>
      </AirCard>
    </section>

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
import SortIcon from '@/components/prompt_library/SortIcon.vue'

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

const expandedResult = ref(null)
function toggleExpand(uid) { expandedResult.value = expandedResult.value === uid ? null : uid }

const resultsSort = ref({ key: 'trend', dir: 'desc' })
function toggleResultsSort(key) {
  if (resultsSort.value.key === key) {
    resultsSort.value.dir = resultsSort.value.dir === 'asc' ? 'desc' : 'asc'
  } else {
    resultsSort.value = { key, dir: key === 'trend' ? 'desc' : 'asc' }
  }
  resultsPage.value = 1
}
function resultsSortState(key) {
  if (resultsSort.value.key !== key) return null
  return resultsSort.value.dir
}

const filteredGeneratedPrompts = computed(() => {
  let rows = generatedPrompts.value
  if (generatedStyleFilter.value) {
    rows = rows.filter(p => p.style === generatedStyleFilter.value)
  }
  const { key, dir } = resultsSort.value
  const factor = dir === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    let av, bv
    if (key === 'trend') { av = a.trend_score ?? 0; bv = b.trend_score ?? 0 }
    else if (key === 'style') { av = a.style || ''; bv = b.style || '' }
    else if (key === 'status') { av = a._saved ? 1 : 0; bv = b._saved ? 1 : 0 }
    else { av = a._uid; bv = b._uid }
    if (av < bv) return -1 * factor
    if (av > bv) return 1 * factor
    return 0
  })
})

const RESULTS_PAGE_SIZE = 10
const resultsPage = ref(1)
const resultsPageCount = computed(() => Math.max(1, Math.ceil(filteredGeneratedPrompts.value.length / RESULTS_PAGE_SIZE)))
const pagedGeneratedPrompts = computed(() => {
  const start = (resultsPage.value - 1) * RESULTS_PAGE_SIZE
  return filteredGeneratedPrompts.value.slice(start, start + RESULTS_PAGE_SIZE)
})
const resultsRangeStart = computed(() => filteredGeneratedPrompts.value.length === 0 ? 0 : (resultsPage.value - 1) * RESULTS_PAGE_SIZE + 1)
const resultsRangeEnd = computed(() => Math.min(filteredGeneratedPrompts.value.length, resultsPage.value * RESULTS_PAGE_SIZE))

function formatRowId(p) {
  // After save: show the first chunk of the persisted UUID so it's
  // recognisable as a real DB record. Before save: show the stable
  // client-generated alphanumeric.
  if (p._savedId) return String(p._savedId).slice(0, 8).toUpperCase()
  return p._displayId || '—'
}
function wordCountOf(p) {
  const t = (p?.prompt_text || p?.template_text || '').trim()
  return t ? t.split(/\s+/).filter(Boolean).length : 0
}

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
function _newDisplayId() {
  // 5-character alphanumeric, like "K3F7Q". Stable for the lifetime of the
  // generated prompt; replaced by the persisted UUID after save.
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let out = ''
  for (let i = 0; i < 5; i++) {
    out += alphabet[Math.floor(Math.random() * alphabet.length)]
  }
  return out
}
function _wrap(item) {
  _genUid += 1
  return {
    _uid: 'g' + _genUid,
    _displayId: _newDisplayId(),
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
.pl-hero-title {
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0;
}
.pl-hero-sub {
  margin: 10px auto 0;
  max-width: 36rem;
  font-size: 15px;
  line-height: 1.55;
  color: var(--text-secondary);
}

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

.pl-row { transition: background 0.12s ease-out; cursor: pointer; }
.pl-row:hover { background: var(--bg-surface, rgba(0, 0, 0, 0.02)); }
.pl-row.is-expanded { background: var(--bg-surface, rgba(0, 0, 0, 0.02)); }

.pl-data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  text-align: left;
  font-size: 14px;
  color: var(--text-primary);
}
.pl-th {
  padding: 14px 16px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0;
  text-transform: none;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-surface, rgba(0, 0, 0, 0.02));
}
.pl-th.sortable { cursor: pointer; user-select: none; }
.pl-th.sortable:hover { color: var(--text-primary); }
.pl-th-inner { display: inline-flex; align-items: center; gap: 6px; }
.pl-th-inner.justify-end { justify-content: flex-end; }

.pl-td {
  padding: 16px;
  vertical-align: middle;
  border-top: 1px solid var(--border-color);
}
.pl-td-prompt { max-width: 56rem; }
.pl-prompt-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.55;
}

.pl-id-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 14px;
  border-radius: 9999px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
  letter-spacing: 0.02em;
}

.pl-status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
}
.pl-status-pill.is-pending {
  background: rgba(180, 83, 9, 0.10);
  color: var(--color-warning, #b45309);
}
.pl-status-pill.is-signed {
  background: rgba(16, 185, 129, 0.12);
  color: var(--color-success, #059669);
}

.pl-action-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
}
.pl-expand-toggle {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.pl-expand-toggle:hover { background: var(--bg-surface); color: var(--text-primary); }

.pl-detail-row { background: var(--bg-surface, rgba(0, 0, 0, 0.025)); }
.pl-detail-cell { padding: 20px 24px; border-top: 1px solid var(--border-color); }
.pl-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 18px 28px;
  margin-bottom: 18px;
}
.pl-detail-block { display: flex; flex-direction: column; gap: 4px; }
.pl-detail-label {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.pl-detail-value {
  font-size: 14px;
  color: var(--text-primary);
}
.pl-detail-prompt {
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
  margin-bottom: 16px;
}
.pl-detail-fulltext {
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-primary);
  margin: 0;
}
.pl-detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
  justify-content: flex-end;
}

.pl-table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-top: 1px solid var(--border-color);
  font-size: 13px;
  color: var(--text-secondary);
}
.pl-table-foot-info strong { color: var(--text-primary); font-weight: 500; }
.pl-pagination { display: flex; gap: 6px; }
.pl-page-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 9999px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.pl-page-btn:hover:not(:disabled) {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--text-primary);
}
.pl-page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Trend column header tooltip ─────────────────────────────── */
.pl-info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: 4px;
  border-radius: 9999px;
  color: var(--text-muted);
  cursor: help;
  position: relative;
  transition: color 0.15s, background 0.15s;
}
.pl-info-icon:hover, .pl-info-icon:focus { color: var(--text-primary); background: var(--bg-card); outline: none; }
.pl-tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translate(-50%, 8px);
  width: 320px;
  padding: 14px 16px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12), 0 1px 4px rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  line-height: 1.5;
  text-align: left;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
  z-index: 30;
}
.pl-info-icon:hover .pl-tooltip,
.pl-info-icon:focus .pl-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translate(-50%, 6px);
  pointer-events: auto;
}
.pl-tooltip strong { display: block; font-size: 12px; font-weight: 600; margin-bottom: 6px; color: var(--text-primary); }
.pl-tooltip p { margin: 0 0 8px; color: var(--text-secondary); }
.pl-tooltip ul { margin: 0 0 8px; padding-left: 18px; color: var(--text-secondary); }
.pl-tooltip ul li { margin: 0 0 4px; }
.pl-tooltip ul b { color: var(--text-primary); font-weight: 500; }
.pl-tooltip-foot { margin: 6px 0 0; padding-top: 8px; border-top: 1px solid var(--border-color); color: var(--text-muted); font-size: 11px; }

/* ── Empty state inside the results table ───────────────────── */
.pl-empty-row td { padding: 0; }
.pl-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56px 24px;
  gap: 8px;
}
.pl-empty-icon {
  width: 64px;
  height: 64px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.04));
  color: var(--text-muted);
  margin-bottom: 6px;
}
.pl-empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
.pl-empty-sub {
  font-size: 14px;
  color: var(--text-muted);
  max-width: 32rem;
  line-height: 1.55;
}

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
