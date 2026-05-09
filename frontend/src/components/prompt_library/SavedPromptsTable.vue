<template>
  <div class="spt-wrap">
    <!-- Stat tiles -->
    <div v-if="prompts.length" class="spt-stat-grid">
      <div class="spt-stat-tile">
        <div class="spt-stat-icon" style="background: rgba(91, 141, 239, 0.12); color: var(--brand-accent)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3 8-8" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2h11" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <div class="spt-stat-label">Total saved</div>
          <div class="spt-stat-val">{{ prompts.length }}</div>
        </div>
      </div>
      <div class="spt-stat-tile">
        <div class="spt-stat-icon" style="background: rgba(16, 185, 129, 0.12); color: var(--color-success, #059669)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <div class="spt-stat-label">Tested</div>
          <div class="spt-stat-val">{{ testedCount }}</div>
        </div>
      </div>
      <div class="spt-stat-tile">
        <div class="spt-stat-icon" style="background: rgba(180, 83, 9, 0.10); color: var(--color-warning, #b45309)">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01" stroke-linecap="round"/></svg>
        </div>
        <div>
          <div class="spt-stat-label">Untested</div>
          <div class="spt-stat-val">{{ untestedCount }}</div>
        </div>
      </div>
      <div class="spt-stat-tile">
        <div class="spt-stat-icon" style="background: rgba(126, 34, 206, 0.10); color: #7e22ce">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l6-6 4 4 8-8" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 7h4v4" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <div class="spt-stat-label">Avg trend</div>
          <div class="spt-stat-val">{{ avgTrend }}</div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div v-if="prompts.length" class="spt-filters">
      <input v-model="search" type="search" class="spt-search" placeholder="Filter saved prompts…" />
      <label class="spt-select-wrap">
        <span class="spt-select-label">Style</span>
        <select v-model="styleFilter" class="spt-select">
          <option value="">All</option>
          <option v-for="s in styleOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </label>
      <label class="spt-select-wrap">
        <span class="spt-select-label">Source</span>
        <select v-model="sourceFilter" class="spt-select">
          <option value="">All</option>
          <option value="deepseek">DeepSeek</option>
          <option value="manual">Manual</option>
          <option value="reddit">Reddit</option>
          <option value="serpapi">SerpAPI</option>
          <option value="claude">Claude</option>
        </select>
      </label>
      <AirButton variant="primary" size="sm" :as="'router-link'" :to="`/llm-ranking/${websiteId}`">
        Run audit
      </AirButton>
    </div>

    <AirCard size="md" :padded="false">
      <div v-if="loading" class="spt-state">Loading saved prompts…</div>
      <div v-else-if="!prompts.length" class="spt-empty">
        <div class="spt-empty-icon" aria-hidden="true">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="spt-empty-title">No saved prompts yet</div>
        <p class="spt-empty-sub">
          Run a search and click <strong>Save</strong> on any prompt to add it
          here. Once you've saved a few, run an audit on the LLM Ranking page
          to start measuring visibility.
        </p>
        <AirButton variant="primary" size="sm" @click="$emit('go-search')">
          Search prompts
        </AirButton>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="spt-table">
          <thead>
            <tr>
              <th style="width: 110px">ID</th>
              <th style="width: 120px">Style</th>
              <th>Prompt</th>
              <th style="width: 110px">Source</th>
              <th style="width: 130px">Last tested</th>
              <th style="width: 130px">Status</th>
              <th style="width: 110px" class="text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredPrompts" :key="row.id" class="spt-row">
              <td><span class="spt-id-pill">{{ formatId(row.id) }}</span></td>
              <td><AirChip size="xs" variant="neutral">{{ titleCase(row.style) }}</AirChip></td>
              <td class="spt-prompt-cell"><div class="spt-prompt-text">{{ row.text || row.template_text }}</div></td>
              <td><AirChip size="xs" variant="info">{{ row.source || 'manual' }}</AirChip></td>
              <td class="spt-muted">{{ row.last_tested_at ? formatRelative(row.last_tested_at) : '—' }}</td>
              <td>
                <span v-if="!row.runs_count" class="spt-status spt-status-untested">Untested</span>
                <span v-else-if="(row.effectiveness_score || 0) >= 0.7" class="spt-status spt-status-good">Top</span>
                <span v-else-if="(row.effectiveness_score || 0) >= 0.4" class="spt-status spt-status-mid">Steady</span>
                <span v-else class="spt-status spt-status-low">Underperforming</span>
              </td>
              <td class="text-right">
                <button class="spt-action-btn" :disabled="testingId === row.id" @click="onTest(row)" :title="`Smoke test against Claude`">
                  <span v-if="testingId === row.id" class="spt-spinner"></span>
                  <span v-else>Test</span>
                </button>
                <button class="spt-action-btn spt-action-btn-ghost" @click="onRemove(row)" title="Remove from saved">×</button>
              </td>
            </tr>
            <tr v-if="!filteredPrompts.length">
              <td colspan="7" class="spt-empty-filter">No prompts match these filters.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </AirCard>

    <BaseModal v-model="smokeOpen" title="Test result" subtitle="Single-provider smoke test" wide>
      <SmokeTestResult v-if="smokeResult" :result="smokeResult" @try-provider="(p) => runSmoke(activeSmokePromptId, p)" />
      <div v-else class="spt-state">Running…</div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import promptLibrary from '@/api/promptLibrary'
import AirCard from '@/components/ui/AirCard.vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import SmokeTestResult from '@/components/prompt_library/SmokeTestResult.vue'

const props = defineProps({
  websiteId: { type: String, required: true },
})
defineEmits(['go-search'])

const toast = useToast()

const prompts = ref([])
const loading = ref(false)
const search = ref('')
const styleFilter = ref('')
const sourceFilter = ref('')
const testingId = ref(null)
const smokeOpen = ref(false)
const smokeResult = ref(null)
const activeSmokePromptId = ref(null)

const styleOptions = [
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

const filteredPrompts = computed(() => {
  const q = search.value.trim().toLowerCase()
  return prompts.value.filter(p => {
    if (styleFilter.value && p.style !== styleFilter.value) return false
    if (sourceFilter.value && (p.source || 'manual') !== sourceFilter.value) return false
    if (q) {
      const t = (p.text || p.template_text || '').toLowerCase()
      if (!t.includes(q)) return false
    }
    return true
  })
})

const testedCount = computed(() => prompts.value.filter(p => (p.runs_count || 0) > 0).length)
const untestedCount = computed(() => prompts.value.length - testedCount.value)
const avgTrend = computed(() => {
  if (!prompts.value.length) return '—'
  const scores = prompts.value
    .map(p => Number(p.effectiveness_score) ? Math.round(Number(p.effectiveness_score) * 100) : null)
    .filter(s => s !== null)
  if (!scores.length) return '—'
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
})

function titleCase(value) {
  if (!value) return '—'
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
function formatId(uuid) {
  return String(uuid || '').replace(/-/g, '').slice(0, 5).toUpperCase()
}
function formatRelative(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const sec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  if (sec < 86400 * 7) return `${Math.floor(sec / 86400)}d ago`
  return d.toLocaleDateString()
}

async function load() {
  if (!props.websiteId) return
  loading.value = true
  try {
    const { data } = await promptLibrary.listBrandPrompts(props.websiteId)
    const rows = data?.data?.results || data?.results || data?.data || data || []
    const list = Array.isArray(rows) ? rows : []
    prompts.value = list.map(item => item.prompt
      ? { ...item.prompt, _brand_prompt_id: item.id, notes: item.notes }
      : item
    )
  } catch (e) {
    prompts.value = []
    toast.error('Could not load saved prompts.')
  } finally {
    loading.value = false
  }
}

async function runSmoke(promptId, provider = 'claude') {
  if (!promptId) return
  testingId.value = promptId
  smokeOpen.value = true
  smokeResult.value = null
  activeSmokePromptId.value = promptId
  try {
    const { data } = await promptLibrary.smokeTest(promptId, { provider, website_id: props.websiteId })
    smokeResult.value = data?.data || data
  } catch (e) {
    smokeOpen.value = false
    toast.error(e.displayMessage || 'Smoke test failed.')
  } finally {
    testingId.value = null
  }
}

function onTest(row) { runSmoke(row.id, 'claude') }

async function onRemove(row) {
  if (!row._brand_prompt_id) return
  if (!window.confirm('Remove this prompt from your saved set?')) return
  try {
    await promptLibrary.removeBrandPrompt(row._brand_prompt_id)
    prompts.value = prompts.value.filter(p => p._brand_prompt_id !== row._brand_prompt_id)
    toast.success('Removed.')
  } catch (e) {
    toast.error('Could not remove.')
  }
}

defineExpose({ load, count: computed(() => prompts.value.length) })

onMounted(load)
watch(() => props.websiteId, load)
</script>

<style scoped>
.spt-wrap { display: flex; flex-direction: column; gap: 16px; }

.spt-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.spt-stat-tile {
  display: flex; align-items: center; gap: 14px;
  padding: 18px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.spt-stat-icon { width: 40px; height: 40px; display: inline-flex; align-items: center; justify-content: center; border-radius: 12px; flex-shrink: 0; }
.spt-stat-label { font-size: 12px; color: var(--text-secondary); margin: 0; }
.spt-stat-val { font-size: 22px; font-weight: 600; color: var(--text-primary); margin-top: 2px; font-variant-numeric: tabular-nums; }

.spt-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.spt-search {
  flex: 1; min-width: 220px;
  padding: 8px 14px; border: 1px solid var(--border-color); border-radius: 9999px;
  background: var(--bg-card); color: var(--text-primary); font-size: 14px; outline: none;
}
.spt-search:focus-visible { border-color: var(--brand-accent); box-shadow: 0 0 0 3px var(--brand-accent-glow); }
.spt-select-wrap { display: inline-flex; align-items: center; gap: 8px; }
.spt-select-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.spt-select {
  appearance: none; -webkit-appearance: none;
  background-color: var(--bg-card);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2364748b' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 10px center;
  border: 1px solid var(--border-color); border-radius: 9999px;
  color: var(--text-primary); padding: 6px 30px 6px 12px;
  font-size: 13px; cursor: pointer;
}

.spt-table { width: 100%; border-collapse: separate; border-spacing: 0; }
.spt-table thead th {
  padding: 14px 16px; font-size: 12px; font-weight: 500;
  color: var(--text-muted); text-align: left;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-surface, rgba(0, 0, 0, 0.02));
}
.spt-table tbody td {
  padding: 14px 16px; border-top: 1px solid var(--border-color);
  font-size: 14px; vertical-align: middle; color: var(--text-primary);
}
.spt-row:hover td { background: var(--bg-surface, rgba(0, 0, 0, 0.02)); }
.spt-prompt-cell { max-width: 56rem; }
.spt-prompt-text {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; line-height: 1.5;
}
.spt-id-pill {
  display: inline-flex; align-items: center; padding: 4px 12px;
  border-radius: 9999px; border: 1px solid var(--border-color);
  background: var(--bg-card); font-size: 12px;
  font-variant-numeric: tabular-nums; color: var(--text-secondary);
}
.spt-muted { color: var(--text-muted); font-size: 13px; }

.spt-status { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 9999px; font-size: 11.5px; font-weight: 500; }
.spt-status-untested { background: rgba(180, 83, 9, 0.10); color: var(--color-warning, #b45309); }
.spt-status-good { background: rgba(16, 185, 129, 0.12); color: var(--color-success, #059669); }
.spt-status-mid { background: rgba(91, 141, 239, 0.12); color: var(--brand-accent); }
.spt-status-low { background: rgba(220, 38, 38, 0.10); color: #b91c1c; }

.spt-action-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 30px; padding: 0 14px;
  background: var(--brand-accent); color: #fff; border: 0;
  border-radius: 9999px;
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: filter 0.15s ease, opacity 0.15s ease;
}
.spt-action-btn:hover:not(:disabled) { filter: brightness(0.96); }
.spt-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spt-action-btn-ghost {
  background: transparent; color: var(--text-muted);
  margin-left: 4px; width: 28px; padding: 0;
  font-size: 18px; line-height: 1;
}
.spt-action-btn-ghost:hover { background: var(--bg-surface, rgba(0, 0, 0, 0.04)); color: var(--color-danger, #dc2626); }
.spt-spinner {
  width: 12px; height: 12px;
  border: 2px solid currentColor; border-right-color: transparent;
  border-radius: 50%; animation: spt-spin 0.7s linear infinite;
}
@keyframes spt-spin { to { transform: rotate(360deg); } }

.spt-state, .spt-empty-filter {
  padding: 32px 24px; text-align: center; font-size: 14px; color: var(--text-muted);
}
.spt-empty {
  display: flex; flex-direction: column; align-items: center;
  text-align: center; padding: 56px 24px; gap: 8px;
}
.spt-empty-icon {
  width: 64px; height: 64px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 9999px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.04));
  color: var(--text-muted); margin-bottom: 6px;
}
.spt-empty-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.spt-empty-sub { font-size: 14px; color: var(--text-muted); max-width: 32rem; line-height: 1.55; margin: 0 0 12px; }
</style>
