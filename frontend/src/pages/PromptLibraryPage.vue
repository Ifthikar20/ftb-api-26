<template>
  <div class="pl-page">
    <!-- Header -->
    <header id="pl-header" class="page-header pl-hero">
      <span class="pl-hero-eyebrow">Prompt library</span>
      <h1 class="pl-hero-title">What are AI assistants saying about you?</h1>
      <p class="pl-hero-sub">
        Describe a scenario. We'll surface the prompts buyers are likely typing
        into ChatGPT, Claude, and Perplexity right now — and benchmark you
        against the brands they hear back.
      </p>
    </header>

    <!-- Tab toggle: Search vs Saved -->
    <div class="pl-tabs" role="tablist">
      <span
        class="pl-tab-indicator"
        :style="{ transform: `translateX(${activeTab === 'saved' ? '100%' : '0%'})` }"
        aria-hidden="true"
      ></span>
      <button
        class="pl-tab"
        :class="{ 'is-active': activeTab === 'search' }"
        role="tab"
        :aria-selected="activeTab === 'search'"
        @click="activeTab = 'search'"
      >
        <svg class="pl-tab-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7" stroke-linecap="round"/>
          <path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
        </svg>
        <span>Search</span>
      </button>
      <button
        class="pl-tab"
        :class="{ 'is-active': activeTab === 'saved' }"
        role="tab"
        :aria-selected="activeTab === 'saved'"
        @click="activeTab = 'saved'"
      >
        <svg class="pl-tab-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>Saved</span>
        <span v-if="savedTableRef && savedTableRef.count" class="pl-tab-count">
          {{ savedTableRef.count }}
        </span>
      </button>
    </div>

    <!-- SAVED tab -->
    <section v-if="activeTab === 'saved'" class="pl-section">
      <SavedPromptsTable
        ref="savedTableRef"
        :website-id="websiteId"
        @go-search="activeTab = 'search'"
      />
    </section>

    <template v-else>
    <!-- Context input -->
    <section class="pl-section pl-section-search">
      <ContextInputCard
        v-model="contextInput"
        v-model:count="promptCount"
        :loading="generating"
        @generate="onGenerate"
      />
    </section>

    <!-- Generated results -->
    <section class="pl-section pl-section-results">
      <!-- Stat strip -->
      <div v-if="generatedPrompts.length" class="pl-stat-strip">
        <div class="pl-stat-cell">
          <span class="pl-stat-label">Total prompts</span>
          <span class="pl-stat-val">{{ generatedPrompts.length }}</span>
        </div>
        <div class="pl-stat-cell">
          <span class="pl-stat-label">Avg trend</span>
          <span class="pl-stat-val">{{ avgTrend }}</span>
        </div>
        <div class="pl-stat-cell">
          <span class="pl-stat-label">Trending</span>
          <span class="pl-stat-val">{{ trendingCount }}</span>
          <span class="pl-stat-hint">≥70</span>
        </div>
        <div class="pl-stat-cell">
          <span class="pl-stat-label">Saved</span>
          <span class="pl-stat-val">{{ savedCount }}</span>
        </div>
        <div class="pl-stat-cell">
          <span class="pl-stat-label">Categories</span>
          <span class="pl-stat-val">{{ categoryCount }}</span>
        </div>
      </div>

      <div class="pl-section-head">
        <h2 class="pl-section-title">
          <template v-if="generatedPrompts.length">
            {{ generatedPrompts.length }} results
            <span v-if="generationProvider" class="pl-section-sub-inline">· {{ generationProvider }}</span>
          </template>
          <template v-else>Results</template>
        </h2>

        <div class="pl-head-actions">
          <label v-if="generatedPrompts.length" class="pl-select-wrap">
            <span class="pl-select-label">Style</span>
            <select v-model="generatedStyleFilter" class="pl-select">
              <option v-for="s in generatedStyleFilters" :key="'gs-' + s.value" :value="s.value">
                {{ s.label }}
              </option>
            </select>
          </label>
          <label v-if="generatedPrompts.length" class="pl-select-wrap">
            <span class="pl-select-label">Length</span>
            <select v-model="generatedLengthFilter" class="pl-select">
              <option v-for="l in generatedLengthFilters" :key="'gl-' + l.value" :value="l.value">
                {{ l.label }}
              </option>
            </select>
          </label>
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
      </div>


      <AirCard size="md" :padded="false">
        <!-- Skeleton rows while we wait for the synthesis call to come back.
             More tactile than a spinning bar — feels like the table is
             populating itself. -->
        <div v-if="generating && !generatedPrompts.length" class="pl-skeleton-wrap">
          <div class="pl-skeleton-status">
            <span class="pl-skeleton-pulse"></span>
            <span>Loading your prompt library…</span>
          </div>
          <div v-for="n in 4" :key="'sk-' + n" class="pl-skeleton-row" :style="{ animationDelay: (n * 0.12) + 's' }">
            <div class="pl-skel-prompt-col">
              <div class="pl-skel pl-skel-line w-85"></div>
              <div class="pl-skel pl-skel-line w-55"></div>
            </div>
            <div class="pl-skel pl-skel-action"></div>
          </div>
        </div>

        <!-- Empty / error state — rendered outside the table so there's no
             horizontal scrollbar when there's nothing to show -->
        <div v-else-if="!generatedPrompts.length" class="pl-empty-state">
          <div class="pl-empty-icon" aria-hidden="true">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="7" stroke-linecap="round"/>
              <path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
            </svg>
          </div>
          <div v-if="generationError" class="pl-empty-title">No prompts for that scenario</div>
          <div v-else class="pl-empty-title">No prompts yet</div>
          <div class="pl-empty-sub">
            <template v-if="generationError">Try adding a few more words or a specific place.</template>
            <template v-else>Type a scenario above and hit Search to populate this table.</template>
          </div>
        </div>

        <div v-else class="pl-table-wrap">
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
              <template v-for="(p, idx) in pagedGeneratedPrompts" :key="p._uid">
                <tr
                  class="pl-row pl-row-stagger"
                  :class="{ 'is-expanded': expandedResult === p._uid }"
                  :style="{ animationDelay: Math.min(idx, 12) * 28 + 'ms' }"
                  @click="toggleExpand(p._uid)"
                >
                  <td class="pl-td">
                    <span class="pl-id-pill">{{ formatRowId(p) }}</span>
                  </td>
                  <td class="pl-td">
                    <AirChip size="xs" variant="neutral">{{ titleCaseStyle(p.style) }}</AirChip>
                  </td>
                  <td class="pl-td pl-td-prompt">
                    <span class="pl-prompt-text" v-html="renderHighlighted(p.prompt_text || p.template_text, p.keywords)"></span>
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
                <tr class="pl-detail-row" :class="{ 'is-open': expandedResult === p._uid }">
                  <td colspan="6" class="pl-detail-cell">
                    <div class="pl-detail-inner">
                      <div class="pl-detail-grid">
                        <div class="pl-detail-block">
                          <div class="pl-detail-label">Last seen on</div>
                          <div class="pl-detail-value">
                            <span class="pl-source-chip" :class="'is-' + (p.seen_in || 'ai_chat')">
                              <span class="pl-source-dot"></span>
                              {{ seenInLabel(p.seen_in) }}
                              <template v-if="p.community"> · {{ p.community }}</template>
                            </span>
                          </div>
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
                          <div class="pl-detail-label">Length</div>
                          <div class="pl-detail-value">{{ wordCountOf(p) }} words · <span style="color: var(--text-muted)">{{ titleCaseStyle(lengthBandOf(p)) }}</span></div>
                        </div>
                        <div class="pl-detail-block">
                          <div class="pl-detail-label">Trend score</div>
                          <div class="pl-detail-value">{{ p.trend_score ?? '—' }} / 100 · <span style="color: var(--text-muted)">{{ trendLabel(p.trend_score) }}</span></div>
                        </div>
                        <div class="pl-detail-block">
                          <div class="pl-detail-label">Sentiment</div>
                          <div class="pl-detail-value">{{ sentimentOf(p) }}</div>
                        </div>
                        <div class="pl-detail-block">
                          <div class="pl-detail-label">Question type</div>
                          <div class="pl-detail-value">{{ questionTypeOf(p) }}</div>
                        </div>
                        <div class="pl-detail-block">
                          <div class="pl-detail-label">Suggested LLMs</div>
                          <div class="pl-detail-value">
                            <AirChip v-for="prov in suggestedProviders(p)" :key="prov" size="xs" variant="neutral" class="mr-1">{{ prov }}</AirChip>
                          </div>
                        </div>
                      </div>
                      <div class="pl-detail-block-wide">
                        <div class="pl-detail-label">Keywords highlighted</div>
                        <div class="pl-detail-value">
                          <span v-if="!p.keywords || !p.keywords.length" style="color: var(--text-muted)">No keywords detected</span>
                          <span v-else>
                            <AirChip v-for="kw in p.keywords" :key="kw" size="xs" variant="warning" class="mr-1 mb-1">{{ kw }}</AirChip>
                          </span>
                        </div>
                      </div>
                      <div class="pl-detail-prompt">
                        <div class="pl-detail-label mb-1">Full prompt</div>
                        <p class="pl-detail-fulltext" v-html="renderHighlighted(p.prompt_text || p.template_text, p.keywords)"></p>
                      </div>

                      <!-- Who's asking similar questions, grouped by source -->
                      <div class="pl-detail-sources">
                        <div class="pl-detail-label mb-2">Who's asking similar questions</div>
                        <div v-if="searchSourcesByUid[p._uid]?.loading" class="pl-sources-state">
                          Looking it up on Google…
                        </div>
                        <div v-else-if="searchSourcesByUid[p._uid]?.unconfigured" class="pl-sources-state">
                          Add a SerpAPI key in your environment to see who's asking similar questions on Google.
                        </div>
                        <div v-else-if="searchSourcesByUid[p._uid]?.error" class="pl-sources-state">
                          Couldn't fetch live sources. Try again later.
                        </div>
                        <div v-else-if="searchSourcesByUid[p._uid]?.groups?.length" class="pl-asker-groups">
                          <div
                            v-for="g in searchSourcesByUid[p._uid].groups"
                            :key="g.source_class"
                            class="pl-asker-group"
                          >
                            <div class="pl-asker-group-head">
                              <span class="pl-asker-group-title">
                                <span class="pl-asker-source-dot" :class="'is-' + g.source_class"></span>
                                {{ titleCaseStyle(g.source_class) }}
                              </span>
                              <span class="pl-asker-group-count">
                                {{ g.count }} {{ g.count === 1 ? 'asker' : 'askers' }}
                                <template v-if="g.communities && g.communities.length">
                                  · {{ g.communities.slice(0, 2).join(' · ') }}
                                </template>
                              </span>
                            </div>
                            <ul class="pl-asker-list">
                              <li v-for="(a, ai) in g.askers" :key="a.url + '-' + ai" class="pl-asker-row">
                                <a :href="a.url" target="_blank" rel="noopener" class="pl-asker-link">
                                  <span class="pl-asker-avatar">{{ avatarInitial(a) }}</span>
                                  <span class="pl-asker-body">
                                    <span class="pl-asker-line">
                                      <span class="pl-asker-handle">{{ a.asker || displayDomain(a.domain) }}</span>
                                      <span v-if="a.community" class="pl-asker-community">{{ a.community }}</span>
                                      <span v-if="a.posted_at" class="pl-asker-when">{{ a.posted_at }}</span>
                                    </span>
                                    <span class="pl-asker-question">{{ a.title }}</span>
                                    <span v-if="a.snippet" class="pl-asker-snippet">{{ a.snippet }}</span>
                                  </span>
                                  <span class="pl-asker-go" aria-hidden="true">↗</span>
                                </a>
                              </li>
                            </ul>
                          </div>
                        </div>
                        <div v-else class="pl-sources-state">
                          No similar public questions found for this prompt yet.
                        </div>
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
    </template>

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
import SavedPromptsTable from '@/components/prompt_library/SavedPromptsTable.vue'

const route = useRoute()
const toast = useToast()
const appStore = useAppStore()
const { activeWebsite } = storeToRefs(appStore)

const websiteId = computed(() => route.params.websiteId || activeWebsite.value?.id || null)

// ── Tab state (Search vs Saved) ──
const activeTab = ref(route?.query?.tab === 'saved' ? 'saved' : 'search')
const savedTableRef = ref(null)
watch(activeTab, (v) => {
  if (v === 'saved' && savedTableRef.value?.load) savedTableRef.value.load()
})
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
// How many prompts to ask the LLM to generate. Capped at 50 by the
// backend serializer; the slider lets users dial it back when they
// just want a quick sample.
const promptCount = ref(20)
const generating = ref(false)
const generatedPrompts = ref([]) // { _uid, _saved, _saving, template_text, ... }
const generationProvider = ref('')
const generationError = ref(false)
const generatedStyleFilter = ref('')
const generatedStyleFilters = [
  { value: '', label: 'All' },
  { value: 'story', label: 'Story' },
  { value: 'question', label: 'Question' },
  { value: 'recommendation', label: 'Recommendation' },
  { value: 'skeptical', label: 'Skeptical' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'local', label: 'Local' },
  { value: 'how_to', label: 'How-to' },
  { value: 'discovery', label: 'Discovery' },
  { value: 'problem', label: 'Problem' },
  { value: 'verification', label: 'Verification' },
  { value: 'experience', label: 'Experience' },
  { value: 'listicle', label: 'Listicle' },
]

const generatedLengthFilter = ref('')
const generatedLengthFilters = [
  { value: '', label: 'All' },
  { value: 'short', label: 'Short' },
  { value: 'medium', label: 'Medium' },
  { value: 'long', label: 'Long' },
]
function lengthBandOf(p) {
  if (p.length_band) return p.length_band
  const wc = (p.prompt_text || p.template_text || '').trim().split(/\s+/).filter(Boolean).length
  if (wc <= 14) return 'short'
  if (wc <= 30) return 'medium'
  return 'long'
}

const expandedResult = ref(null)
const searchSourcesByUid = ref({})

function toggleExpand(uid) {
  expandedResult.value = expandedResult.value === uid ? null : uid
  if (expandedResult.value === uid) loadSearchSources(uid)
}

async function loadSearchSources(uid) {
  if (searchSourcesByUid.value[uid]?.results) return // already loaded
  if (searchSourcesByUid.value[uid]?.loading) return
  const prompt = generatedPrompts.value.find(p => p._uid === uid)
  if (!prompt) return
  const text = (prompt.prompt_text || prompt.template_text || '').trim()
  if (!text) return
  searchSourcesByUid.value = { ...searchSourcesByUid.value, [uid]: { loading: true } }
  try {
    const { data } = await promptLibrary.searchSources(text)
    const payload = data?.data || data || {}
    if (payload.provider === 'unconfigured') {
      searchSourcesByUid.value = { ...searchSourcesByUid.value, [uid]: { unconfigured: true, results: [] } }
    } else {
      searchSourcesByUid.value = {
        ...searchSourcesByUid.value,
        [uid]: { results: payload.results || [], provider: payload.provider },
      }
    }
  } catch (e) {
    searchSourcesByUid.value = {
      ...searchSourcesByUid.value,
      [uid]: { error: true, results: [] },
    }
  }
}

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
  if (generatedLengthFilter.value) {
    rows = rows.filter(p => lengthBandOf(p) === generatedLengthFilter.value)
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

function seenInLabel(key) {
  const map = {
    reddit: 'Reddit',
    quora: 'Quora',
    google_search: 'Google search',
    hacker_news: 'Hacker News',
    yelp: 'Yelp',
    tiktok: 'TikTok',
    youtube_comments: 'YouTube comments',
    twitter: 'X / Twitter',
    forum: 'Forum',
    news_comments: 'News comments',
    ai_chat: 'AI chat',
  }
  return map[key] || 'AI chat'
}

function trendBarClass(score) {
  const s = Number(score) || 0
  if (s >= 70) return 'is-hot'
  if (s >= 40) return 'is-warm'
  return 'is-cool'
}

const avgTrend = computed(() => {
  if (!generatedPrompts.value.length) return '—'
  const sum = generatedPrompts.value.reduce((a, p) => a + (Number(p.trend_score) || 0), 0)
  return Math.round(sum / generatedPrompts.value.length)
})
const trendingCount = computed(() => generatedPrompts.value.filter(p => (p.trend_score || 0) >= 70).length)
const savedCount = computed(() => generatedPrompts.value.filter(p => p._saved).length)
const categoryCount = computed(() => new Set(generatedPrompts.value.map(p => p.style).filter(Boolean)).size)

// Heuristic sentiment label from prompt text — cheap client-side derivation
// so the detail panel can show something meaningful without a round-trip.
function sentimentOf(p) {
  const t = (p?.prompt_text || p?.template_text || '').toLowerCase()
  if (!t) return '—'
  if (/(scam|fraud|fake|delusion|gimmick|sketchy|shady|legit|trust|lying|hype)/.test(t)) return 'Skeptical'
  if (/(love|amazing|incredible|legendary|best|favourite|favorite|insane|genius)/.test(t)) return 'Excited'
  if (/(can't|cannot|hate|frustrat|annoy|terrible|awful|bad|worst|stuck)/.test(t)) return 'Frustrated'
  if (/(\?\s*$)/.test(t.trim())) return 'Curious'
  return 'Neutral'
}

function questionTypeOf(p) {
  const t = (p?.prompt_text || p?.template_text || '').trim()
  if (!t) return '—'
  if (/^(what|who|where|when|why|how)\b/i.test(t)) return 'Open-ended'
  if (/\b(or)\b.*\?/i.test(t)) return 'Either / or'
  if (/(should i|do i|is it|is this|are they)/i.test(t)) return 'Yes / no'
  if (/(best|top|recommend)/i.test(t)) return 'Recommendation'
  if (t.endsWith('?')) return 'Direct'
  return 'Statement'
}

function avatarInitial(asker) {
  const handle = (asker?.asker || '').replace(/^u\/|^@/, '')
  if (handle) return handle.charAt(0).toUpperCase()
  const dom = (asker?.domain || '').replace(/^www\./, '')
  if (dom) return dom.charAt(0).toUpperCase()
  return '?'
}

function displayDomain(host) {
  return (host || '').replace(/^www\./, '').split('.').slice(0, -1).join('.') || host
}

const ALL_PROVIDERS = ['Claude', 'GPT-4', 'Gemini', 'Perplexity']
function suggestedProviders(p) {
  // Suggest providers based on trend and style. Trending high-volume
  // queries should always hit Perplexity (cited results); local + how-to
  // prefer Gemini grounded; story-style is conversational so Claude/GPT.
  const out = new Set(['Claude', 'GPT-4'])
  const score = Number(p?.trend_score) || 0
  if (score >= 70) out.add('Perplexity')
  if (['local', 'how_to', 'verification'].includes(p?.style)) out.add('Gemini')
  if (['recommendation', 'comparison', 'listicle'].includes(p?.style)) out.add('Perplexity')
  if ((p?.keywords || []).some(k => /\b(near me|in [a-z]+)\b/i.test(k))) out.add('Gemini')
  return ALL_PROVIDERS.filter(x => out.has(x))
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

/**
 * Render `text` with each phrase in `keywords` wrapped in a highlight span.
 * Case-insensitive. Longer phrases take priority so 'kettle-boiling or just
 * steaming' wins over 'kettle' alone. Builds the output by walking the raw
 * string once and escape-encoding only the non-keyword chunks, so we can't
 * accidentally inject HTML into the user's keywords.
 */
function renderHighlighted(text, keywords) {
  if (!text) return ''
  if (!keywords || !keywords.length) return _escapeHtml(text)
  const sorted = [...keywords].filter(Boolean).sort((a, b) => b.length - a.length)
  const lower = text.toLowerCase()
  const ranges = []
  for (const raw of sorted) {
    const kw = String(raw).trim()
    if (kw.length < 2) continue
    const target = kw.toLowerCase()
    let idx = 0
    while (true) {
      const pos = lower.indexOf(target, idx)
      if (pos === -1) break
      const end = pos + target.length
      const overlaps = ranges.some(r => pos < r.end && end > r.start)
      if (!overlaps) ranges.push({ start: pos, end })
      idx = pos + 1
    }
  }
  if (!ranges.length) return _escapeHtml(text)
  ranges.sort((a, b) => a.start - b.start)
  let out = ''
  let cursor = 0
  for (const r of ranges) {
    if (r.start > cursor) out += _escapeHtml(text.slice(cursor, r.start))
    out += `<mark class="pl-mark">${_escapeHtml(text.slice(r.start, r.end))}</mark>`
    cursor = r.end
  }
  if (cursor < text.length) out += _escapeHtml(text.slice(cursor))
  return out
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

async function onGenerate(text, count) {
  generating.value = true
  generationError.value = false
  // Honour the slider when present; fall back to whatever the parent
  // last persisted into promptCount.
  const requested = Number(count) || promptCount.value || 20
  const clamped = Math.max(1, Math.min(50, requested))
  promptCount.value = clamped
  try {
    const { data } = await promptLibrary.generateFromContext({
      context: text,
      count: clamped,
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
    toast.success('Saved · view in the Saved tab')
    loadPrompts()
    // If the saved-tab table is mounted, refresh its count + list
    if (savedTableRef.value?.load) savedTableRef.value.load()
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
/* ── Full-width dashboard layout ──────────────────────────── */
.pl-page {
  --pl-accent: #ff6a2c;
  --pl-accent-soft: rgba(255, 106, 44, 0.10);
  --pl-spring: cubic-bezier(0.22, 1, 0.36, 1);
  --pl-spring-strong: cubic-bezier(0.16, 1, 0.3, 1);

  position: relative;
  width: 100%;
  max-width: none;
  padding: 32px 40px 48px;
  margin: 0;
  background: var(--bg-root, var(--bg-page, #fafafa));
  min-height: 100%;
  overflow-x: hidden;
}
/* Ambient hero glow behind the header — same trick used in the
   onboarding modal and paywall so the search bar feels like the
   focal point of a real library/search app. */
.pl-page::before {
  content: '';
  position: absolute;
  top: -120px;
  left: 50%;
  width: 820px;
  height: 480px;
  transform: translateX(-50%);
  background: radial-gradient(ellipse at center, var(--pl-accent-soft) 0%, transparent 65%);
  filter: blur(48px);
  pointer-events: none;
  opacity: 0.7;
  z-index: 0;
}
.pl-page > * { position: relative; z-index: 1; }

.pl-page-header {
  margin-bottom: 28px;
  text-align: left;
  max-width: 720px;
  animation: pl-rise 0.55s var(--pl-spring-strong) both;
}
@keyframes pl-rise {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Library-style hero ───────────────────────────────────── */
.pl-hero {
  display: flex;
  flex-direction: column;
  text-align: center;
  align-items: center;
  margin: 0 auto 32px;
  max-width: 720px;
}
.pl-hero-eyebrow {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 14px;
  font-weight: 600;
}
.pl-hero-title {
  font-size: clamp(28px, 3.4vw, 40px);
  line-height: 1.08;
  font-weight: 600;
  letter-spacing: -0.025em;
  color: var(--text-primary);
  margin: 0 0 12px;
}
.pl-hero-sub {
  font-size: 15px;
  line-height: 1.55;
  color: var(--text-muted);
  margin: 0;
  max-width: 560px;
}
/* Centre the tabs row under the centred hero. */
.pl-tabs { margin-left: auto; margin-right: auto; }

/* ── Tabs (Search / Saved) ──────────────────────────────────── */
.pl-tabs {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 5px;
  background: var(--bg-surface, rgba(15, 23, 42, 0.06));
  border-radius: 9999px;
  margin-bottom: 28px;
  isolation: isolate;
}
.pl-tab-indicator {
  position: absolute;
  top: 5px;
  bottom: 5px;
  left: 5px;
  width: calc(50% - 5px);
  background: var(--bg-card, #ffffff);
  border-radius: 9999px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.06),
    0 4px 12px rgba(15, 23, 42, 0.06);
  transition: transform 0.45s var(--pl-spring-strong, cubic-bezier(0.32, 0.72, 0, 1));
  z-index: 0;
}

/* ── Framer-style staggered entry on result rows ────────────
   Each row fades up with a small delay set inline (Math.min(idx,12)
   * 28ms) so the table feels like it's populating itself instead
   of slamming in all at once. */
.pl-row-stagger {
  animation: pl-row-in 0.42s var(--pl-spring-strong) both;
}
@keyframes pl-row-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.pl-row {
  transition: background-color 0.22s var(--pl-spring),
              transform 0.22s var(--pl-spring),
              box-shadow 0.28s var(--pl-spring);
}
.pl-row:hover:not(.is-expanded) {
  transform: translateY(-1px);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04),
              0 10px 22px rgba(15, 23, 42, 0.05);
}

.pl-tab {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 22px;
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  border-radius: 9999px;
  cursor: pointer;
  transition: color 0.2s ease;
  letter-spacing: 0.005em;
  flex: 1;
  justify-content: center;
  min-width: 130px;
}
.pl-tab-icon {
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.pl-tab:hover { color: var(--text-primary); }
.pl-tab:hover .pl-tab-icon { opacity: 0.85; }
.pl-tab.is-active {
  color: var(--text-primary);
  font-weight: 600;
}
.pl-tab.is-active .pl-tab-icon { opacity: 1; transform: scale(1.05); }
.pl-tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 9999px;
  background: var(--brand-accent);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.pl-section { margin-bottom: 32px; }
.pl-section-search { display: flex; justify-content: center; }
.pl-section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.pl-section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.pl-section-sub-inline { color: var(--text-muted); font-weight: 400; }

/* ── Stat tiles ───────────────────────────────────────────── */
.pl-stat-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 22px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 12px;
}
.pl-stat-cell {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}
.pl-stat-cell + .pl-stat-cell {
  padding-left: 22px;
  border-left: 1px solid var(--border-color);
}
.pl-stat-strip .pl-stat-label {
  font-size: 11.5px;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
  color: var(--text-secondary);
}
.pl-stat-strip .pl-stat-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.pl-stat-strip .pl-stat-hint {
  font-size: 10.5px;
  color: var(--text-muted, #94a3b8);
}
@media (max-width: 600px) {
  .pl-stat-cell + .pl-stat-cell { padding-left: 0; border-left: 0; }
  .pl-stat-strip { gap: 12px 18px; }
}

.pl-hero-title {
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0;
}
.pl-hero-sub {
  margin: 8px 0 0;
  max-width: 36rem;
  font-size: 15px;
  line-height: 1.55;
  color: var(--text-secondary);
}

/* Section head — title left, dropdowns + Search-again right */
.pl-head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.pl-select-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.pl-select-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.pl-select {
  appearance: none;
  -webkit-appearance: none;
  background-color: var(--bg-card);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2364748b' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  border: 1px solid var(--border-color);
  border-radius: 9999px;
  color: var(--text-primary);
  padding: 6px 30px 6px 12px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.pl-select:focus-visible {
  outline: none;
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px var(--brand-accent-glow);
}

/* Sources panel inside the expanded detail */
.pl-detail-sources {
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
  margin-top: 4px;
  margin-bottom: 16px;
}
.pl-sources-state {
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 0;
}
.pl-sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pl-source-row {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.pl-source-row:hover { border-color: var(--text-muted); box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06); }
.pl-source-link {
  display: block;
  padding: 12px 14px;
  text-decoration: none;
  color: inherit;
}
.pl-source-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.pl-source-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.35;
}
.pl-source-host {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.pl-source-snippet {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Who's asking — grouped view ──────────────────────────── */
.pl-asker-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pl-asker-group {
  border: 1px solid var(--border-color);
  border-radius: 14px;
  overflow: hidden;
  background: var(--bg-card);
}
.pl-asker-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.025));
  border-bottom: 1px solid var(--border-color);
}
.pl-asker-group-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.pl-asker-source-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--text-muted);
  flex-shrink: 0;
}
.pl-asker-source-dot.is-reddit { background: #ff4500; }
.pl-asker-source-dot.is-quora { background: #b92b27; }
.pl-asker-source-dot.is-stackoverflow { background: #f48024; }
.pl-asker-source-dot.is-wikipedia { background: #555; }
.pl-asker-source-dot.is-youtube { background: #ff0000; }
.pl-asker-source-dot.is-social { background: #0ea5e9; }
.pl-asker-source-dot.is-review { background: #d97706; }
.pl-asker-source-dot.is-news { background: #2563eb; }
.pl-asker-source-dot.is-blog { background: #7e22ce; }
.pl-asker-source-dot.is-gov { background: #059669; }
.pl-asker-source-dot.is-edu { background: #4338ca; }
.pl-asker-source-dot.is-other { background: #94a3b8; }
.pl-asker-group-count {
  font-size: 12px;
  color: var(--text-muted);
}
.pl-asker-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.pl-asker-row + .pl-asker-row { border-top: 1px solid var(--border-color); }
.pl-asker-link {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  text-decoration: none;
  color: inherit;
  transition: background 0.12s;
}
.pl-asker-link:hover { background: var(--bg-surface, rgba(0, 0, 0, 0.025)); }
.pl-asker-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 9999px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.06));
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}
.pl-asker-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.pl-asker-line {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.pl-asker-handle {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.pl-asker-community {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-surface, rgba(0, 0, 0, 0.04));
  padding: 1px 8px;
  border-radius: 9999px;
}
.pl-asker-when {
  font-size: 11px;
  color: var(--text-muted);
}
.pl-asker-question {
  font-size: 13.5px;
  color: var(--text-primary);
  line-height: 1.4;
  margin-top: 2px;
}
.pl-asker-snippet {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.45;
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pl-asker-go {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 14px;
  align-self: center;
  opacity: 0;
  transition: opacity 0.12s;
}
.pl-asker-link:hover .pl-asker-go { opacity: 1; }

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
.pl-filter-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  flex-shrink: 0;
  width: 60px;
  padding-top: 6px;
}
.pl-filters-stack { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.pl-filter-row { display: flex; align-items: flex-start; gap: 12px; }
.pl-filter-chips { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; }

:deep(.pl-mark) {
  background: linear-gradient(180deg, transparent 25%, #fff3a8 25%, #fff3a8 95%, transparent 95%);
  color: var(--text-primary);
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 500;
}
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

.pl-table-wrap {
  /* Only show the horizontal scrollbar if the table actually overflows on
     a small viewport. The table fills its container otherwise. */
  overflow-x: auto;
}
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

/* ── Animated detail expansion ─────────────────────────────── */
.pl-detail-row { background: var(--bg-surface, rgba(0, 0, 0, 0.025)); }
.pl-detail-cell { padding: 0; border: 0; }
.pl-detail-inner {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  padding: 0 28px;
  border-top: 1px solid transparent;
  transition:
    max-height 0.32s cubic-bezier(0.4, 0.0, 0.2, 1),
    opacity 0.18s ease,
    padding 0.32s cubic-bezier(0.4, 0.0, 0.2, 1),
    border-color 0.18s ease;
}
.pl-detail-row.is-open .pl-detail-inner {
  max-height: 1400px;
  opacity: 1;
  padding: 24px 28px 28px;
  border-top: 1px solid var(--border-color);
}
.pl-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 20px 28px;
  margin-bottom: 18px;
}
.pl-detail-block-wide {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 16px;
  margin-bottom: 4px;
  border-top: 1px solid var(--border-color);
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
/* ── Skeleton loading rows ──────────────────────────────────── */
.pl-skeleton-wrap {
  padding: 28px 24px 36px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.pl-skeleton-status {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 14px;
  padding: 8px 14px;
  background: var(--bg-surface, rgba(15, 23, 42, 0.04));
  border-radius: 9999px;
  align-self: flex-start;
}
.pl-skeleton-pulse {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--brand-accent);
  box-shadow: 0 0 0 0 var(--brand-accent-glow, rgba(91, 141, 239, 0.5));
  animation: pl-skel-pulse 1.4s ease-out infinite;
}
@keyframes pl-skel-pulse {
  70%  { box-shadow: 0 0 0 8px rgba(91, 141, 239, 0); }
  100% { box-shadow: 0 0 0 0  rgba(91, 141, 239, 0); }
}
.pl-skeleton-row {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 22px 20px;
  background: var(--bg-elevated, rgba(15, 23, 42, 0.02));
  border: 1px solid var(--border-color);
  border-radius: 12px;
  opacity: 0;
  animation: pl-skel-fade 0.4s ease-out forwards;
}
@keyframes pl-skel-fade { to { opacity: 1; } }
.pl-skel {
  background: linear-gradient(
    90deg,
    rgba(15, 23, 42, 0.04) 0%,
    rgba(15, 23, 42, 0.10) 50%,
    rgba(15, 23, 42, 0.04) 100%
  );
  background-size: 200% 100%;
  animation: pl-skel-shimmer 1.4s ease-in-out infinite;
  border-radius: 6px;
  height: 14px;
}
@keyframes pl-skel-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.pl-skel-prompt-col { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.pl-skel-line    { height: 14px; }
.pl-skel-line.w-85 { width: 85%; }
.pl-skel-line.w-55 { width: 55%; }
.pl-skel-action  { width: 88px; height: 32px; border-radius: 9999px; flex-shrink: 0; }

/* ── Source / 'Last seen on' chip in the expanded detail ────── */
.pl-source-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-surface, rgba(15, 23, 42, 0.04));
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}
.pl-source-dot {
  width: 7px; height: 7px; border-radius: 9999px;
  background: var(--text-muted);
  flex-shrink: 0;
}
.pl-source-chip.is-reddit           { background: rgba(255, 69, 0, 0.10);  color: #c4400a; }
.pl-source-chip.is-reddit .pl-source-dot { background: #ff4500; }
.pl-source-chip.is-quora            { background: rgba(185, 43, 39, 0.10); color: #9b2420; }
.pl-source-chip.is-quora .pl-source-dot { background: #b92b27; }
.pl-source-chip.is-google_search    { background: rgba(66, 133, 244, 0.10); color: #1f57c1; }
.pl-source-chip.is-google_search .pl-source-dot { background: #4285f4; }
.pl-source-chip.is-hacker_news      { background: rgba(255, 102, 0, 0.10); color: #c44d00; }
.pl-source-chip.is-hacker_news .pl-source-dot { background: #ff6600; }
.pl-source-chip.is-yelp             { background: rgba(217, 38, 41, 0.10); color: #ad1f22; }
.pl-source-chip.is-yelp .pl-source-dot { background: #d92629; }
.pl-source-chip.is-tiktok           { background: rgba(0, 0, 0, 0.06); color: #1a1a1a; }
.pl-source-chip.is-tiktok .pl-source-dot { background: linear-gradient(135deg, #25f4ee, #fe2c55); }
.pl-source-chip.is-youtube_comments { background: rgba(255, 0, 0, 0.10); color: #b80000; }
.pl-source-chip.is-youtube_comments .pl-source-dot { background: #ff0000; }
.pl-source-chip.is-twitter          { background: rgba(15, 20, 25, 0.06); color: #1a1f24; }
.pl-source-chip.is-twitter .pl-source-dot { background: #0f1419; }
.pl-source-chip.is-forum            { background: rgba(20, 116, 110, 0.10); color: #0e6660; }
.pl-source-chip.is-forum .pl-source-dot { background: #14746e; }
.pl-source-chip.is-news_comments    { background: rgba(37, 99, 235, 0.10); color: #1d4ed8; }
.pl-source-chip.is-news_comments .pl-source-dot { background: #2563eb; }
.pl-source-chip.is-ai_chat          { background: rgba(126, 34, 206, 0.10); color: #6e21b8; }
.pl-source-chip.is-ai_chat .pl-source-dot { background: #7e22ce; }

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
